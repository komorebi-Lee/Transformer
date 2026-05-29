"""Fine-tune chinese_t5_pegasus_base for sentence → abstract code generation.

Trains a seq2seq model that maps interview sentences to abstract first-level codes.
Uses v11 training data with teacher forcing and cross-entropy loss.

Usage:
    D:\\anaconda3\\envs\\zthree5\\python.exe train_t5_abstract_coding.py
    D:\\anaconda3\\envs\\zthree5\\python.exe train_t5_abstract_coding.py --epochs 20 --batch-size 8
    D:\\anaconda3\\envs\\zthree5\\python.exe train_t5_abstract_coding.py --test
"""

import argparse
import json
import logging
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
logger = logging.getLogger("train_t5")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------
# Dataset
# ------------------------------------------------------------------

class AbstractCodingDataset(Dataset):
    """(sentence, abstract_code) pairs from v11 training data."""

    def __init__(
        self,
        v11_path: str,
        tokenizer,
        max_src_len: int = 256,
        max_tgt_len: int = 32,
        max_samples: Optional[int] = None,
    ):
        self.tokenizer = tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len

        with open(v11_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        training_data = data.get("training_data", [])
        if max_samples and len(training_data) > max_samples:
            random.seed(42)
            training_data = random.sample(training_data, max_samples)

        self.pairs: List[Tuple[str, str]] = []
        seen: set = set()
        for item in training_data:
            sent = str(
                (item.get("input_sentences", {}) or {}).get("original_content", "")
            ).strip()
            abstract = str(item.get("target_abstract", "")).strip()
            if not sent or not abstract:
                continue
            key = sent + "|||" + abstract
            if key in seen:
                continue
            seen.add(key)
            self.pairs.append((sent, abstract))

        logger.info("Dataset: %d unique (sentence, abstract) pairs", len(self.pairs))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        src, tgt = self.pairs[idx]
        src_ids, _ = self.tokenizer.encode(src, maxlen=self.max_src_len)
        # Target: encode with start token, add end token
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

        # Teacher forcing: decoder input = target[:-1], labels = target[1:]
        dec_input_ids = tgt_ids[:, :-1]
        labels = tgt_ids[:, 1:]

        optimizer.zero_grad()

        # encoder output: [hidden_states, attention_bias]
        enc_out = model.encoder(src_ids)

        # decoder output is already logits: [B, T, vocab_size]
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
    """Generate abstract codes using model.generate()."""
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
        # Fallback: simple generation
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

    if isinstance(outputs, list):
        seqs = outputs
    elif hasattr(outputs, 'sequences'):
        seqs = outputs.sequences
    else:
        seqs = outputs

    for seq in seqs:
        if hasattr(seq, 'tolist'):
            seq = seq.tolist()
        code = tokenizer.decode(seq)
        code = code.strip()
        if not code or code in seen:
            continue
        seen.add(code)
        results.append((code, 0.0))  # Score not available in simple mode

    return results if results else [("", 0.0)]


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    model_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "local_models", "chinese_t5_pegasus_base",
    )
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "trained_models", "t5_abstract_coding",
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

    logger.info("Loading model ...")
    model = build_transformer_model(
        config_path=os.path.join(model_dir, "bert4torch_config.json"),
        checkpoint_path=os.path.join(model_dir, "pytorch_model.bin"),
        model="mt5.1.1",
    )
    model.to(device)
    n_params = sum(p.numel() for p in model.parameters())
    logger.info("Model loaded: %.1fM params", n_params / 1e6)

    # ---- Test mode ----
    if args.test:
        logger.info("=== Inference Test ===")
        # Try loading fine-tuned model if available
        ft_path = os.path.join(output_dir, "pytorch_model.bin")
        if os.path.exists(ft_path):
            logger.info("Loading fine-tuned weights from %s", ft_path)
            model.load_state_dict(torch.load(ft_path, map_location=device))

        test_sentences = [
            "资源不够，审批流程太复杂",
            "培训不到位，员工能力参差不齐",
            "市场需求变化快，产品跟不上",
            "管理制度不完善，缺乏监督机制",
            "资金不足导致项目推进缓慢",
        ]
        for sent in test_sentences:
            results = generate_codes(model, tokenizer, sent, device)
            print(f"\nSource: {sent}")
            for code, score in results[:3]:
                print(f"  [{score:.4f}] {code}")
        return 0

    # ---- Prepare data ----
    dataset = AbstractCodingDataset(
        v11_path=args.v11_path,
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

    # ---- Training ----
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    best_val_loss = float("inf")

    logger.info("Starting training: %d epochs, batch_size=%d, lr=%g",
                args.epochs, args.batch_size, args.lr)

    for epoch in range(args.epochs):
        t0 = time.time()

        train_loss = train_epoch(model, train_loader, optimizer, device)
        val_metrics = validate(model, val_loader, device)
        scheduler.step()
        elapsed = time.time() - t0

        logger.info("Epoch %d/%d (%.1fs): train_loss=%.4f, val_loss=%.4f, lr=%.2e",
                    epoch + 1, args.epochs, elapsed,
                    train_loss, val_metrics["loss"], scheduler.get_last_lr()[0])

        # Save best
        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            os.makedirs(output_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(output_dir, "pytorch_model.bin"))

            import shutil
            for fname in ["bert4torch_config.json", "vocab.txt"]:
                src = os.path.join(model_dir, fname)
                dst = os.path.join(output_dir, fname)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy(src, dst)
            logger.info("  Best model saved (val_loss=%.4f)", best_val_loss)

        # Sample every 3 epochs
        if (epoch + 1) % 3 == 0:
            idx = random.randint(0, len(val_ds) - 1)
            src_text, gold = val_ds.dataset.pairs[val_ds.indices[idx]]
            results = generate_codes(model, tokenizer, src_text, device)
            pred = results[0][0] if results else ""
            logger.info("  Sample: src='%s'", src_text[:100])
            logger.info("    Gold: '%s'", gold)
            logger.info("    Pred: '%s'", pred)

    logger.info("Training complete. Best val_loss=%.4f", best_val_loss)


if __name__ == "__main__":
    main()
