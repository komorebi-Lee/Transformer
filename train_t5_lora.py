"""LoRA fine-tuning of t5-pegasus for first-level abstract code generation.

Uses Low-Rank Adaptation (LoRA) to fine-tune only ~2-3M parameters of the
275M-param T5 model. This prevents overfitting on the limited 7130-pair dataset.

LoRA is applied to the query (q) and value (v) projection matrices in all
attention layers (both encoder and decoder).

Usage:
    D:/anaconda3/envs/zthree5/python.exe train_t5_lora.py --epochs 20 --batch-size 8
    D:/anaconda3/envs/zthree5/python.exe train_t5_lora.py --test  # inference test
"""

import argparse
import csv
import json
import logging
import math
import os
import random
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_t5_lora")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------
# LoRA Layer
# ------------------------------------------------------------------

class LoRALinear(nn.Module):
    """Low-rank adaptation wrapper for nn.Linear.

    W' = W + (alpha / r) * A @ B

    where A is (in_features, r) and B is (r, out_features).
    During training, only A and B are updated; W is frozen.
    """

    def __init__(self, linear: nn.Linear, r: int = 8, alpha: float = 16.0,
                 dropout: float = 0.05):
        super().__init__()
        self.linear = linear  # frozen original
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / r

        # Freeze original weights
        self.linear.weight.requires_grad = False
        if self.linear.bias is not None:
            self.linear.bias.requires_grad = False

        in_features = linear.in_features
        out_features = linear.out_features
        device = linear.weight.device

        # LoRA parameters: A ~ N(0, 1/k), B = 0, on same device as original
        self.lora_A = nn.Parameter(
            torch.randn(in_features, r, device=device) * (1.0 / math.sqrt(in_features))
        )
        self.lora_B = nn.Parameter(torch.zeros(r, out_features, device=device))
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x):
        base_out = self.linear(x)
        if self.lora_A.device != x.device:
            self.lora_A.data = self.lora_A.data.to(x.device)
            self.lora_B.data = self.lora_B.data.to(x.device)
        lora_out = self.dropout(x) @ self.lora_A @ self.lora_B
        return base_out + lora_out * self.scaling

    @property
    def weight(self):
        return self.linear.weight

    @property
    def bias(self):
        return self.linear.bias


def apply_lora_to_t5(model, r: int = 8, alpha: float = 16.0,
                     dropout: float = 0.05, target_modules: List[str] = None) -> int:
    """Replace Linear layers in T5 attention with LoRA-wrapped versions.

    First freezes ALL model parameters, then applies LoRA to q/v projections
    in both self-attention and cross-attention of encoder and decoder.
    Returns the number of LoRA-applied layers.
    """
    # Freeze everything first
    for p in model.parameters():
        p.requires_grad = False

    if target_modules is None:
        target_modules = ['q', 'v']

    count = 0
    for part_name in ['encoder', 'decoder']:
        part = getattr(model, part_name, None)
        if part is None:
            continue
        for attr in ['encoderLayerList', 'encoderLayer', 'decoderLayerList', 'decoderLayer']:
            block_list = getattr(part, attr, None)
            if block_list is not None:
                break
        if block_list is None:
            continue
        for block in block_list:
            count += _apply_lora_to_block(block, r, alpha, dropout, target_modules)

    logger.info("Applied LoRA (r=%d, alpha=%.1f) to %d Linear layers", r, alpha, count)
    return count


def _apply_lora_to_block(block, r, alpha, dropout, target_modules) -> int:
    """Replace targeted Linear layers in one transformer block with LoRALinear."""
    count = 0
    for name, module in list(block.named_modules()):
        if not isinstance(module, nn.Linear):
            continue
        # Check if this is a target module (q/v projection)
        if not any(name.endswith(f'.{t}') or name == t for t in target_modules):
            continue
        parent = block
        parts = name.split('.')
        for p in parts[:-1]:
            parent = getattr(parent, p)
        lora = LoRALinear(module, r=r, alpha=alpha, dropout=dropout)
        setattr(parent, parts[-1], lora)
        count += 1
    return count


def count_lora_params(model) -> Tuple[int, int]:
    """Return (trainable_LoRA_params, total_params)."""
    lora = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return lora, total


# ------------------------------------------------------------------
# Dataset
# ------------------------------------------------------------------

class CombinedCodingDataset(Dataset):
    """(sentence, abstract_code) pairs from v11 + CSV data for LoRA training."""

    def __init__(
        self,
        v11_path: str,
        csv_dir: str,
        tokenizer,
        max_src_len: int = 256,
        max_tgt_len: int = 32,
        max_samples: Optional[int] = None,
    ):
        self.tokenizer = tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len

        pairs: List[Tuple[str, str]] = []
        seen: set = set()

        # 1. Load v11
        with open(v11_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data.get("training_data", []):
            sent = str(
                (item.get("input_sentences", {}) or {}).get("original_content", "")
            ).strip()
            abstract = str(item.get("target_abstract", "")).strip()
            if sent and abstract and (sent, abstract) not in seen:
                seen.add((sent, abstract))
                pairs.append((sent, abstract))
        logger.info("v11: %d pairs", len(pairs))

        # 2. Load CSV
        csv_files = [
            ("final_standard.csv", "gbk"),
            ("standard_augmented.csv", "utf-8"),
            ("standard.csv", "gbk"),
            ("standard2.csv", "utf-8"),
        ]
        for fname, enc in csv_files:
            path = os.path.join(csv_dir, fname)
            if not os.path.exists(path):
                continue
            count = 0
            with open(path, "r", encoding=enc, errors="replace") as fh:
                reader = csv.reader(fh)
                next(reader, None)
                for row in reader:
                    if len(row) < 2:
                        continue
                    code = row[0].strip()
                    text = row[1].strip()
                    if not code or not text or code.lower() == "nan":
                        continue
                    if (text, code) in seen:
                        continue
                    seen.add((text, code))
                    pairs.append((text, code))
                    count += 1
            logger.info("  %s: %d pairs", fname, count)

        if max_samples and len(pairs) > max_samples:
            random.seed(42)
            pairs = random.sample(pairs, max_samples)

        self.pairs = pairs
        logger.info("Dataset: %d unique (sentence, abstract_code) pairs", len(self.pairs))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        src, tgt = self.pairs[idx]
        src_ids, _ = self.tokenizer.encode(src, maxlen=self.max_src_len)
        tgt_ids, _ = self.tokenizer.encode(tgt, maxlen=self.max_tgt_len - 1)
        tgt_ids = tgt_ids + [self.tokenizer._token_end_id]
        return {
            "src_ids": src_ids,
            "tgt_ids": tgt_ids,
            "src_text": src,
            "tgt_text": tgt,
        }


def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    from bert4torch.snippets import sequence_padding
    src_ids = sequence_padding([item["src_ids"] for item in batch])
    tgt_ids = sequence_padding([item["tgt_ids"] for item in batch])
    return {
        "src_ids": torch.tensor(src_ids, dtype=torch.long),
        "tgt_ids": torch.tensor(tgt_ids, dtype=torch.long),
        "src_texts": [item["src_text"] for item in batch],
        "tgt_texts": [item["tgt_text"] for item in batch],
    }


# ------------------------------------------------------------------
# Training
# ------------------------------------------------------------------

def train_epoch(model, dataloader, optimizer, device) -> float:
    model.train()
    total_loss = 0.0
    total_tokens = 0
    loss_fn = nn.CrossEntropyLoss(ignore_index=0)

    for batch_idx, batch in enumerate(dataloader):
        src_ids = batch["src_ids"].to(device)
        tgt_ids = batch["tgt_ids"].to(device)
        dec_input_ids = tgt_ids[:, :-1]
        labels = tgt_ids[:, 1:]

        optimizer.zero_grad()
        enc_out = model.encoder(src_ids)
        logits = model.decoder(dec_input_ids, enc_out)
        loss = loss_fn(logits.reshape(-1, logits.size(-1)), labels.reshape(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item() * labels.numel()
        total_tokens += (labels != 0).sum().item()

        if batch_idx % 100 == 0:
            logger.info("  Batch %d/%d, loss=%.4f", batch_idx, len(dataloader), loss.item())

    return total_loss / max(1, total_tokens)


@torch.no_grad()
def validate(model, dataloader, device) -> Dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    loss_fn = nn.CrossEntropyLoss(ignore_index=0)

    for batch in dataloader:
        src_ids = batch["src_ids"].to(device)
        tgt_ids = batch["tgt_ids"].to(device)
        dec_input_ids = tgt_ids[:, :-1]
        labels = tgt_ids[:, 1:]
        enc_out = model.encoder(src_ids)
        logits = model.decoder(dec_input_ids, enc_out)
        loss = loss_fn(logits.reshape(-1, logits.size(-1)), labels.reshape(-1))
        total_loss += loss.item() * labels.numel()
        total_tokens += (labels != 0).sum().item()

    return {"loss": total_loss / max(1, total_tokens)}


@torch.no_grad()
def generate_codes(model, tokenizer, src_text: str, device,
                   max_len: int = 32, beam_size: int = 5) -> List[Tuple[str, float]]:
    """Generate abstract codes using model.generate() with beam search."""
    model.eval()
    src_ids, _ = tokenizer.encode(src_text, maxlen=256)
    src_tensor = torch.tensor([src_ids], dtype=torch.long).to(device)

    try:
        outputs = model.generate(
            src_tensor,
            max_new_tokens=max_len,
            num_beams=beam_size,
            num_return_sequences=min(beam_size, 3),
            eos_token_id=tokenizer._token_end_id,
            pad_token_id=tokenizer._token_pad_id,
            bos_token_id=tokenizer._token_start_id,
            output_scores=True,
            return_dict_in_generate=True,
        )
    except Exception:
        outputs = model.generate(
            src_tensor,
            max_new_tokens=max_len,
            num_beams=beam_size,
            eos_token_id=tokenizer._token_end_id,
            pad_token_id=tokenizer._token_pad_id,
            bos_token_id=tokenizer._token_start_id,
        )

    results: List[Tuple[str, float]] = []
    seen: set = set()

    seqs = outputs if isinstance(outputs, list) else (
        outputs.sequences if hasattr(outputs, 'sequences') else outputs
    )

    for seq in seqs:
        if hasattr(seq, 'tolist'):
            seq = seq.tolist()
        code = tokenizer.decode(seq).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        results.append((code, 0.0))

    return results if results else [("", 0.0)]


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=float, default=16.0)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing LoRA checkpoint")
    parser.add_argument("--early-stopping-patience", type=int, default=80,
                        help="Stop if no improvement for N epochs (0=disable)")
    parser.add_argument("--save-every", type=int, default=50,
                        help="Save checkpoint every N epochs (in addition to best)")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    parser.add_argument("--csv-dir", type=str, default=r"D:\zthree2\csv")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s | LoRA r=%d alpha=%.1f dropout=%.2f",
                device, args.lora_r, args.lora_alpha, args.lora_dropout)

    model_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "local_models", "chinese_t5_pegasus_base",
    )
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "trained_models", "t5_lora_coding",
    )

    # ---- Load model ----
    import jieba
    jieba.initialize()
    from bert4torch.models import build_transformer_model
    from bert4torch.tokenizers import Tokenizer

    tokenizer = Tokenizer(
        os.path.join(model_dir, "vocab.txt"),
        do_lower_case=True,
        pre_tokenize=lambda s: list(jieba.cut(s, HMM=False)),
    )

    logger.info("Loading base model ...")
    model = build_transformer_model(
        config_path=os.path.join(model_dir, "bert4torch_config.json"),
        checkpoint_path=os.path.join(model_dir, "pytorch_model.bin"),
        model="mt5.1.1",
    )
    n_full = sum(p.numel() for p in model.parameters())
    logger.info("Base model: %.1fM params", n_full / 1e6)

    # ---- Apply LoRA (on CPU, before moving to device) ----
    n_lora_layers = apply_lora_to_t5(
        model, r=args.lora_r, alpha=args.lora_alpha,
        dropout=args.lora_dropout,
    )
    lora_params, total_params = count_lora_params(model)
    logger.info("LoRA applied: %d layers, trainable=%.2fM / total=%.1fM",
                n_lora_layers, lora_params / 1e6, total_params / 1e6)

    model.to(device)

    # ---- Resume from checkpoint ----
    start_epoch = 0
    best_val_loss = float("inf")
    checkpoint_path = os.path.join(output_dir, "checkpoint.pt")
    if args.resume and os.path.exists(checkpoint_path):
        logger.info("Resuming from checkpoint: %s", checkpoint_path)
        ckpt = torch.load(checkpoint_path, map_location=device)
        model_state = model.state_dict()
        for key, val in ckpt["lora_state"].items():
            if key in model_state:
                model_state[key].copy_(val)
        start_epoch = ckpt["epoch"] + 1
        best_val_loss = ckpt.get("best_val_loss", float("inf"))
        logger.info("Resumed from epoch %d, best_val_loss=%.4f", ckpt["epoch"], best_val_loss)
    elif args.resume:
        # Fallback: load lora_weights.pt only
        lora_path = os.path.join(output_dir, "lora_weights.pt")
        if os.path.exists(lora_path):
            logger.info("Loading LoRA weights from %s", lora_path)
            lora_state = torch.load(lora_path, map_location=device)
            model_state = model.state_dict()
            for key, val in lora_state.items():
                if key in model_state:
                    model_state[key].copy_(val)
            logger.info("LoRA weights loaded (epoch unknown, starting from 0)")

    # ---- Test mode ----
    if args.test:
        logger.info("=== Inference Test ===")
        ft_path = os.path.join(output_dir, "lora_weights.pt")
        if os.path.exists(ft_path):
            logger.info("Loading LoRA weights from %s", ft_path)
            lora_state = torch.load(ft_path, map_location=device)
            # Load only LoRA params
            model_state = model.state_dict()
            for key, val in lora_state.items():
                if key in model_state:
                    model_state[key].copy_(val)
            logger.info("LoRA weights loaded")

        test_sentences = [
            "资源不够，审批流程太复杂",
            "培训不到位，员工能力参差不齐",
            "市场需求变化快，产品跟不上",
            "管理制度不完善，缺乏监督机制",
            "资金不足导致项目推进缓慢",
            "人手不够，项目推进困难",
        ]
        for sent in test_sentences:
            results = generate_codes(model, tokenizer, sent, device)
            print(f"\nSource: {sent}")
            for code, score in results[:3]:
                print(f"  [{score:.4f}] {code}")
        return 0

    # ---- Prepare data ----
    dataset = CombinedCodingDataset(
        v11_path=args.v11_path,
        csv_dir=args.csv_dir,
        tokenizer=tokenizer,
        max_samples=args.max_samples,
    )

    n_val = max(1, int(len(dataset) * args.val_split))
    n_train = len(dataset) - n_val
    train_ds, val_ds = torch.utils.data.random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )
    logger.info("Train: %d, Val: %d", n_train, n_val)

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        collate_fn=collate_fn, num_workers=0,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        collate_fn=collate_fn, num_workers=0,
    )

    # ---- Optimizer (only LoRA params) ----
    lora_param_list = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(lora_param_list, lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-6,
    )

    # Resume optimizer/scheduler if available
    if args.resume and os.path.exists(checkpoint_path):
        ckpt = torch.load(checkpoint_path, map_location=device)
        if "optimizer" in ckpt:
            optimizer.load_state_dict(ckpt["optimizer"])
            logger.info("Optimizer state restored")
        if "scheduler" in ckpt:
            scheduler.load_state_dict(ckpt["scheduler"])
            logger.info("Scheduler state restored")
        # Fast-forward scheduler to current epoch
        for _ in range(start_epoch):
            scheduler.step()

    patience_counter = 0
    patience = args.early_stopping_patience

    total_epochs = args.epochs
    logger.info("Starting LoRA training: epochs %d→%d, batch_size=%d, lr=%g",
                start_epoch + 1, total_epochs, args.batch_size, args.lr)
    logger.info("Trainable params: %.2fM, early_stopping_patience=%d",
                sum(p.numel() for p in lora_param_list) / 1e6, patience)

    for epoch in range(start_epoch, total_epochs):
        t0 = time.time()

        train_loss = train_epoch(model, train_loader, optimizer, device)
        val_metrics = validate(model, val_loader, device)
        scheduler.step()
        elapsed = time.time() - t0

        logger.info("Epoch %d/%d (%.1fs): train_loss=%.4f, val_loss=%.4f, lr=%.2e",
                    epoch + 1, total_epochs, elapsed,
                    train_loss, val_metrics["loss"], scheduler.get_last_lr()[0])

        improved = val_metrics["loss"] < best_val_loss - 1e-6
        if improved:
            best_val_loss = val_metrics["loss"]
            patience_counter = 0
            os.makedirs(output_dir, exist_ok=True)
            lora_state = {k: v for k, v in model.state_dict().items()
                          if 'lora_A' in k or 'lora_B' in k}
            torch.save(lora_state, os.path.join(output_dir, "lora_weights.pt"))
            # Save full checkpoint for resume
            torch.save({
                "epoch": epoch,
                "lora_state": lora_state,
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "best_val_loss": best_val_loss,
            }, checkpoint_path)
            import shutil
            for fname in ["bert4torch_config.json", "vocab.txt"]:
                src = os.path.join(model_dir, fname)
                dst = os.path.join(output_dir, fname)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy(src, dst)
            logger.info("  Best model saved (val_loss=%.4f)", best_val_loss)
        else:
            patience_counter += 1

        # Periodic checkpoint (for crash recovery)
        if args.save_every > 0 and (epoch + 1) % args.save_every == 0 and not improved:
            os.makedirs(output_dir, exist_ok=True)
            lora_state = {k: v for k, v in model.state_dict().items()
                          if 'lora_A' in k or 'lora_B' in k}
            torch.save({
                "epoch": epoch,
                "lora_state": lora_state,
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "best_val_loss": best_val_loss,
            }, checkpoint_path)
            logger.info("  Periodic checkpoint saved (epoch %d)", epoch + 1)

        # Early stopping
        if patience > 0 and patience_counter >= patience:
            logger.info("Early stopping at epoch %d (no improvement for %d epochs)",
                        epoch + 1, patience)
            break

        # Sample every 10 epochs (was 4, but 500 epochs needs less frequent)
        if (epoch + 1) % 10 == 0:
            idx = random.randint(0, len(val_ds) - 1)
            src_text, gold = dataset.pairs[val_ds.indices[idx]]
            results = generate_codes(model, tokenizer, src_text, device)
            pred = results[0][0] if results else ""
            logger.info("  Sample: src='%s'", src_text[:100])
            logger.info("    Gold: '%s'", gold)
            logger.info("    Pred: '%s'", pred)

    logger.info("Training complete. %d epochs run, best_val_loss=%.4f",
                epoch + 1, best_val_loss)


if __name__ == "__main__":
    main()
