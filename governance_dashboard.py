"""Interactive Semantic Governance Dashboard — Priority 10.

Provides visualization and monitoring for the coding system health:
  - Hierarchy health gauge
  - Network health gauge
  - Theory confidence distribution
  - Edge type distribution
  - Weak node alerts
  - Interactive theory network graph

Usage:
    from governance_dashboard import GovernanceDashboard
    dialog = GovernanceDashboard(parent=self)
    dialog.exec_()
"""

import json
import os
import logging
from collections import defaultdict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget,
    QGroupBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Configure CJK font support
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import numpy as np

logger = logging.getLogger("governance_dashboard")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIERARCHY_HEALTH_PATH = os.path.join(BASE_DIR, "hierarchy_health.json")
NETWORK_HEALTH_PATH = os.path.join(BASE_DIR, "network_health.json")
THEORY_CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
THEORY_NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")
MERGE_PROVENANCE_PATH = os.path.join(BASE_DIR, "hierarchy_merge_provenance.json")


# ── Health Gauge Widget ──────────────────────────────────────────

class HealthGauge(QWidget):
    """Circular health gauge showing score 0-100 with color coding."""

    def __init__(self, title="Health", parent=None):
        super().__init__(parent)
        self.title = title
        self.score = 0
        self.interpretation = ""
        self.setMinimumSize(180, 200)
        self.setMaximumSize(220, 240)

    def set_score(self, score: float, interpretation: str = ""):
        self.score = max(0, min(100, score))
        self.interpretation = interpretation
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h) - 40
        cx, cy = w // 2, h // 2 - 10
        radius = side // 2

        # Background circle
        painter.setPen(QPen(QColor("#e0e0e0"), 12))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Color based on score
        if self.score >= 75:
            color = QColor("#4caf50")  # green
        elif self.score >= 55:
            color = QColor("#ff9800")  # orange
        elif self.score >= 35:
            color = QColor("#f44336")  # red
        else:
            color = QColor("#9c27b0")  # purple/critical

        # Score arc (partial circle)
        painter.setPen(QPen(color, 12))
        span = int(-self.score / 100 * 360 * 16)  # Qt uses 1/16 degree
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 90 * 16, span)

        # Score text
        painter.setPen(QColor("#333333"))
        font = QFont("Arial", 22, QFont.Bold)
        painter.setFont(font)
        painter.drawText(cx - 40, cy - 5, 80, 30, Qt.AlignCenter, f"{self.score:.0f}")

        # Title
        font2 = QFont("Microsoft YaHei", 10)
        painter.setFont(font2)
        painter.drawText(cx - 60, cy + 40, 120, 20, Qt.AlignCenter, self.title)

        # Interpretation (short)
        if self.interpretation:
            font3 = QFont("Microsoft YaHei", 8)
            painter.setFont(font3)
            color_map = {75: "#4caf50", 55: "#ff9800", 35: "#f44336", 0: "#9c27b0"}
            for thresh, clr in color_map.items():
                if self.score >= thresh:
                    painter.setPen(QColor(clr))
                    break
            short = self.interpretation.split("—")[0].strip()[:20]
            painter.drawText(cx - 60, cy + 55, 120, 16, Qt.AlignCenter, short)

        painter.end()


# ── Matplotlib Chart Panel ───────────────────────────────────────

class MplChartCanvas(FigureCanvas):
    """Embedded matplotlib canvas for charts."""

    def __init__(self, parent=None, width=5, height=3.5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)


# ── Overview Tab ─────────────────────────────────────────────────

class OverviewTab(QWidget):
    """Overview tab: health gauges + key metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Top row: health gauges
        gauges_layout = QHBoxLayout()
        self.hierarchy_gauge = HealthGauge("层级结构健康度")
        self.network_gauge = HealthGauge("理论网络健康度")
        gauges_layout.addStretch()
        gauges_layout.addWidget(self.hierarchy_gauge)
        gauges_layout.addStretch()
        gauges_layout.addWidget(self.network_gauge)
        gauges_layout.addStretch()
        layout.addLayout(gauges_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Stats summary grid (two columns)
        stats_layout = QHBoxLayout()

        # Column 1: Hierarchy stats
        hier_group = QGroupBox("层级结构统计")
        hier_layout = QVBoxLayout(hier_group)
        self.hier_labels = {}
        for key in ["total_anchors", "total_l2", "total_l3",
                     "single_anchor_l2", "single_child_l3",
                     "collisions_fixed", "low_conf_remapped"]:
            lbl = QLabel(f"{key}: —")
            lbl.setFont(QFont("Consolas", 9))
            hier_layout.addWidget(lbl)
            self.hier_labels[key] = lbl
        hier_layout.addStretch()
        stats_layout.addWidget(hier_group)

        # Column 2: Network stats
        net_group = QGroupBox("理论网络统计")
        net_layout = QVBoxLayout(net_group)
        self.net_labels = {}
        for key in ["total_nodes", "total_edges", "density",
                     "isolated_nodes", "avg_degree", "avg_confidence",
                     "weak_nodes"]:
            lbl = QLabel(f"{key}: —")
            lbl.setFont(QFont("Consolas", 9))
            net_layout.addWidget(lbl)
            self.net_labels[key] = lbl
        net_layout.addStretch()
        stats_layout.addWidget(net_group)

        layout.addLayout(stats_layout)

        # Charts row
        charts_layout = QHBoxLayout()

        self.conf_chart = MplChartCanvas(self, width=4, height=3)
        charts_layout.addWidget(self.conf_chart)

        self.edge_chart = MplChartCanvas(self, width=4, height=3)
        charts_layout.addWidget(self.edge_chart)

        layout.addLayout(charts_layout)

        # Weak nodes warning
        self.alert_label = QLabel("")
        self.alert_label.setWordWrap(True)
        self.alert_label.setStyleSheet(
            "QLabel { background-color: #fff3e0; border: 1px solid #ff9800; "
            "border-radius: 4px; padding: 8px; font-size: 11pt; }"
        )
        self.alert_label.setVisible(False)
        layout.addWidget(self.alert_label)

    def load_data(self):
        """Load and display overview data."""
        # Load hierarchy health
        try:
            with open(HIERARCHY_HEALTH_PATH, "r", encoding="utf-8") as f:
                hh = json.load(f)
        except Exception:
            hh = None

        # Load network health
        try:
            with open(NETWORK_HEALTH_PATH, "r", encoding="utf-8") as f:
                nh = json.load(f)
        except Exception:
            nh = None

        # Load confidence
        try:
            with open(THEORY_CONFIDENCE_PATH, "r", encoding="utf-8") as f:
                tc = json.load(f)
        except Exception:
            tc = None

        # Update gauges
        if hh:
            after = hh.get("after", hh)
            score = after.get("health_score", 0)
            interp = after.get("interpretation", "")
            self.hierarchy_gauge.set_score(score, interp)

            ts = after.get("totals", {})
            single_l2 = after.get("single_anchor_l2", {})
            single_l3 = after.get("single_child_l3", {})
            mapping = {
                "total_anchors": ts.get("anchors", "—"),
                "total_l2": ts.get("themes", "—"),
                "total_l3": ts.get("theories", "—"),
                "single_anchor_l2": single_l2.get("count", "—"),
                "single_child_l3": single_l3.get("count", "—"),
                "collisions_fixed": after.get("collisions_fixed", "—"),
                "low_conf_remapped": after.get("low_confidence_remapped", "—"),
            }
            for label_key, val in mapping.items():
                if label_key in self.hier_labels:
                    if isinstance(val, float):
                        val = f"{val:.1f}"
                    self.hier_labels[label_key].setText(f"{label_key}: {val}")

        if nh:
            score = nh.get("health_score", 0)
            interp = nh.get("interpretation", "")
            self.network_gauge.set_score(score, interp)

            topo = nh.get("topology", {})
            conf = nh.get("confidence", {})
            mapping = {
                "total_nodes": ("topology", "total_nodes"),
                "total_edges": ("topology", "total_edges"),
                "density": ("topology", "density"),
                "isolated_nodes": ("topology", "isolated_nodes"),
                "avg_degree": ("topology", "avg_degree"),
                "avg_confidence": ("confidence", "avg_confidence"),
                "weak_nodes": ("confidence", "weak_nodes_count"),
            }
            for label_key, (section, json_key) in mapping.items():
                if label_key in self.net_labels:
                    val = nh.get(section, {}).get(json_key, "—")
                    if isinstance(val, float):
                        val = f"{val:.4f}" if label_key == "density" else f"{val:.1f}"
                    self.net_labels[label_key].setText(f"{label_key}: {val}")

        # Confidence distribution chart
        if tc:
            scores = [v["confidence"] for v in tc.get("scores", {}).values()]
            self.conf_chart.fig.clear()
            ax = self.conf_chart.fig.add_subplot(111)
            ax.hist(scores, bins=20, color="#42a5f5", edgecolor="white", alpha=0.85)
            ax.axvline(np.mean(scores), color="#f44336", linestyle="--",
                       label=f'均值={np.mean(scores):.3f}')
            ax.set_title("理论置信度分布")
            ax.set_xlabel("置信度")
            ax.set_ylabel("理论数")
            ax.legend(fontsize=8)
            self.conf_chart.fig.tight_layout()
            self.conf_chart.draw()

        # Edge type distribution chart
        if nh:
            edge_types = nh.get("edge_quality", {}).get("type_distribution", {})
            if edge_types:
                self.edge_chart.fig.clear()
                ax = self.edge_chart.fig.add_subplot(111)
                labels = list(edge_types.keys())
                sizes = list(edge_types.values())
                colors = ["#66bb6a", "#42a5f5", "#ffa726", "#ab47bc", "#ef5350"]
                ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                       colors=colors[:len(labels)], startangle=90)
                ax.set_title("边类型分布")
                self.edge_chart.fig.tight_layout()
                self.edge_chart.draw()

        # Weak node alerts
        if nh:
            weak_count = nh.get("confidence", {}).get("weak_nodes_count", 0)
            orphans = nh.get("orphan_theories", [])
            orphan_count = len(orphans)

            alerts = []
            if weak_count > 0:
                alerts.append(f"⚠ {weak_count} 个弱置信度理论节点需要关注")
            if orphan_count > 0:
                alerts.append(f"⚠ {orphan_count} 个孤立理论: {', '.join(orphans[:5])}"
                              f"{'...' if orphan_count > 5 else ''}")

            if alerts:
                self.alert_label.setText("\n".join(alerts))
                self.alert_label.setVisible(True)
            else:
                self.alert_label.setVisible(False)


# ── Weak Nodes Tab ───────────────────────────────────────────────

class WeakNodesTab(QWidget):
    """Table of weak/isolated theory nodes needing attention."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        info = QLabel("以下理论节点置信度较低或缺少网络连接，可能需要人工审核。")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "理论名称", "置信度", "网络度", "L1锚点数",
            "平均扎根度", "证据句数", "状态"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)

    def load_data(self):
        # Load network health for weak nodes
        try:
            with open(NETWORK_HEALTH_PATH, "r", encoding="utf-8") as f:
                nh = json.load(f)
        except Exception:
            return

        weak_nodes = nh.get("confidence", {}).get("weak_nodes", [])
        orphans = set(nh.get("orphan_theories", []))

        self.table.setRowCount(len(weak_nodes))
        for row, node in enumerate(weak_nodes):
            name = node.get("theory", "")
            conf = node.get("confidence", 0)
            degree = node.get("degree", 0)
            l1_count = node.get("l1_count", 0)
            grounding = node.get("avg_grounding", 0)

            # Determine status
            status_parts = []
            if degree == 0:
                status_parts.append("孤立")
            if conf < 0.4:
                status_parts.append("低置信度")
            if l1_count <= 2:
                status_parts.append("支撑薄弱")
            status = ", ".join(status_parts) if status_parts else "需关注"

            items = [
                QTableWidgetItem(name),
                QTableWidgetItem(f"{conf:.4f}"),
                QTableWidgetItem(str(degree)),
                QTableWidgetItem(str(l1_count)),
                QTableWidgetItem(f"{grounding:.4f}"),
                QTableWidgetItem(str(node.get("sentence_count", 0))),
                QTableWidgetItem(status),
            ]

            # Color coding
            if conf < 0.35 or degree == 0:
                bg = QColor("#ffebee")  # light red
            elif conf < 0.45:
                bg = QColor("#fff3e0")  # light orange
            else:
                bg = QColor("#fffde7")  # light yellow

            for item in items:
                item.setBackground(bg)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, items.index(item), item)

        self.table.resizeColumnsToContents()


# ── Network Graph Tab ────────────────────────────────────────────

class NetworkGraphTab(QWidget):
    """Interactive theory network graph visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.filter_combo_label = QLabel("筛选:")
        ctrl_layout.addWidget(self.filter_combo_label)

        from PyQt5.QtWidgets import QComboBox
        self.min_degree_spin = QComboBox()
        self.min_degree_spin.addItems(["全部", "度≥1", "度≥2", "度≥3", "度≥5"])
        self.min_degree_spin.currentIndexChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.min_degree_spin)

        self.label_size_label = QLabel("节点标注阈值:")
        ctrl_layout.addWidget(self.label_size_label)

        self.label_threshold = QComboBox()
        self.label_threshold.addItems(["全部", "置信度≥0.5", "置信度≥0.6", "仅孤立节点"])
        self.label_threshold.currentIndexChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.label_threshold)

        ctrl_layout.addStretch()

        info_label = QLabel("节点大小=置信度  |  颜色: 绿=高置信 红=低置信  |  边类型: 实线=语义 虚线=弱语义")
        info_label.setStyleSheet("color: #888; font-size: 9pt;")
        ctrl_layout.addWidget(info_label)
        layout.addLayout(ctrl_layout)

        # Canvas
        self.canvas = MplChartCanvas(self, width=8, height=6)
        layout.addWidget(self.canvas)

        # Detail label (shown on hover/click)
        self.detail_label = QLabel("点击节点查看详情")
        self.detail_label.setStyleSheet(
            "QLabel { background-color: #f5f5f5; border-radius: 4px; padding: 6px; }"
        )
        self.detail_label.setMaximumHeight(60)
        layout.addWidget(self.detail_label)

        # Data caches
        self._nodes_data = []
        self._edges_data = []
        self._confidence = {}
        self._layout_pos = None

        # Connect click event
        self.canvas.fig.canvas.mpl_connect('button_press_event', self._on_click)

    def load_data(self):
        """Load network and confidence data."""
        try:
            with open(THEORY_NETWORK_PATH, "r", encoding="utf-8") as f:
                nd = json.load(f)
            self._nodes_data = nd.get("nodes", [])
            self._edges_data = nd.get("edges", [])
        except Exception:
            self._nodes_data = []
            self._edges_data = []

        try:
            with open(THEORY_CONFIDENCE_PATH, "r", encoding="utf-8") as f:
                tc = json.load(f)
            self._confidence = tc.get("scores", {})
        except Exception:
            self._confidence = {}

        self._layout_pos = None  # reset layout
        self._redraw()

    def _redraw(self):
        if not self._nodes_data:
            return

        # Filter by degree
        min_degree = 0
        degree_text = self.min_degree_spin.currentText()
        if "≥1" in degree_text:
            min_degree = 1
        elif "≥2" in degree_text:
            min_degree = 2
        elif "≥3" in degree_text:
            min_degree = 3
        elif "≥5" in degree_text:
            min_degree = 5

        # Compute degrees
        degrees = defaultdict(int)
        for e in self._edges_data:
            degrees[e["source"]] += 1
            degrees[e["target"]] += 1

        # Filter nodes
        node_ids = [n["id"] for n in self._nodes_data
                     if degrees.get(n["id"], 0) >= min_degree]
        node_set = set(node_ids)
        node_index = {nid: i for i, nid in enumerate(node_ids)}

        # Filter edges to matching nodes
        edge_list = [e for e in self._edges_data
                     if e["source"] in node_set and e["target"] in node_set]

        if not node_ids:
            self.canvas.fig.clear()
            self.canvas.draw()
            return

        # Layout (spring-force)
        if self._layout_pos is None or len(node_ids) != len(self._layout_pos):
            pos = self._spring_layout(node_ids, edge_list, node_index)
            self._layout_pos = pos
        else:
            pos = self._layout_pos

        # Label thresholds
        label_mode = self.label_threshold.currentText()
        show_labels = set()
        for nid in node_ids:
            conf = self._confidence.get(nid, {}).get("confidence", 0)
            deg = degrees.get(nid, 0)
            if label_mode == "全部":
                show_labels.add(nid)
            elif "0.6" in label_mode and conf >= 0.6:
                show_labels.add(nid)
            elif "0.5" in label_mode and conf >= 0.5:
                show_labels.add(nid)
            elif "孤立" in label_mode and deg == 0:
                show_labels.add(nid)

        # Draw
        self.canvas.fig.clear()
        ax = self.canvas.fig.add_subplot(111)
        ax.set_aspect('equal')
        ax.axis('off')

        conf_values = [self._confidence.get(nid, {}).get("confidence", 0.3)
                       for nid in node_ids]
        min_conf = min(conf_values) if conf_values else 0
        max_conf = max(conf_values) if conf_values else 1

        # Draw edges
        for edge in edge_list:
            src, tgt = edge["source"], edge["target"]
            if src in node_index and tgt in node_index:
                x1, y1 = pos[src]
                x2, y2 = pos[tgt]
                etype = edge.get("edge_type", "weak_semantic")
                weight = edge.get("weight", 0.1)

                if etype == "semantic":
                    color = "#42a5f5"
                    style = '-'
                    alpha = 0.4
                elif etype == "structural":
                    color = "#66bb6a"
                    style = '-'
                    alpha = 0.5
                elif etype == "strong_structural":
                    color = "#2e7d32"
                    style = '-'
                    alpha = 0.6
                else:  # weak_semantic / grounding
                    color = "#bdbdbd"
                    style = '--'
                    alpha = 0.25

                ax.plot([x1, x2], [y1, y2], linestyle=style, color=color,
                        alpha=alpha, linewidth=max(0.3, weight * 2))

        # Draw nodes
        xs, ys, sizes, colors = [], [], [], []
        for nid in node_ids:
            x, y = pos[nid]
            conf = self._confidence.get(nid, {}).get("confidence", 0.3)
            size = 30 + conf * 150  # node size proportional to confidence
            # Color: green (high conf) → red (low conf)
            ratio = (conf - min_conf) / max(max_conf - min_conf, 0.01)
            r = int(244 - ratio * 200)
            g = int(67 + ratio * 150)
            b = 54
            color_hex = f"#{r:02x}{g:02x}{b:02x}"

            xs.append(x)
            ys.append(y)
            sizes.append(size)
            colors.append(color_hex)

        ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.85, edgecolors='white',
                   linewidth=0.5, zorder=5, picker=5)

        # Labels
        for nid in show_labels:
            if nid in pos:
                x, y = pos[nid]
                conf = self._confidence.get(nid, {}).get("confidence", 0)
                fontsize = 6 + conf * 4
                ax.annotate(nid, (x, y), fontsize=fontsize, ha='center', va='center',
                            color='#333', fontfamily='Microsoft YaHei',
                            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                      alpha=0.7, edgecolor='none'))

        self.canvas.fig.tight_layout(pad=0.5)
        self.canvas.draw()

    def _spring_layout(self, node_ids, edges, node_index, iterations=50):
        """Simple force-directed layout."""
        n = len(node_ids)
        pos = {nid: np.array([np.random.randn() * 0.3, np.random.randn() * 0.3])
               for nid in node_ids}

        # Build adjacency
        adj = defaultdict(list)
        for e in edges:
            adj[e["source"]].append(e["target"])
            adj[e["target"]].append(e["source"])

        # Parameters
        k = 1.0 / max(n ** 0.5, 1)
        t_init = 0.3
        cooling = 0.92

        for it in range(iterations):
            t = t_init * (cooling ** it)
            forces = {nid: np.zeros(2) for nid in node_ids}

            # Repulsion between all pairs
            for i, ni in enumerate(node_ids):
                for j, nj in enumerate(node_ids):
                    if i >= j:
                        continue
                    delta = pos[ni] - pos[nj]
                    dist = max(np.linalg.norm(delta), 0.01)
                    force = k * k / dist
                    direction = delta / dist
                    forces[ni] += direction * force
                    forces[nj] -= direction * force

            # Attraction along edges
            for e in edges:
                src, tgt = e["source"], e["target"]
                if src not in pos or tgt not in pos:
                    continue
                delta = pos[src] - pos[tgt]
                dist = max(np.linalg.norm(delta), 0.01)
                force = dist * dist / k
                direction = delta / dist
                forces[src] -= direction * force
                forces[tgt] += direction * force

            # Apply forces (clamp)
            for nid in node_ids:
                f = forces[nid]
                norm = np.linalg.norm(f)
                if norm > 0:
                    f = f / norm * min(norm, t)
                pos[nid] += f

        # Center and scale
        all_pos = np.array(list(pos.values()))
        center = all_pos.mean(axis=0)
        scale = max(np.std(all_pos), 0.1)
        for nid in pos:
            pos[nid] = (pos[nid] - center) / scale * 2.0

        return pos

    def _on_click(self, event):
        if event.inaxes is None or not self._nodes_data:
            return

        # Find nearest node
        if not hasattr(self, '_layout_pos') or not self._layout_pos:
            return

        click = np.array([event.xdata, event.ydata])
        best_dist = float('inf')
        best_nid = None

        for nid, p in self._layout_pos.items():
            dist = np.linalg.norm(np.array(p) - click)
            if dist < best_dist:
                best_dist = dist
                best_nid = nid

        if best_nid and best_dist < 0.3:
            conf_data = self._confidence.get(best_nid, {})
            conf = conf_data.get("confidence", "—")
            comps = conf_data.get("components", {})
            raw = conf_data.get("raw_metrics", {})

            detail = (
                f"理论: {best_nid}  |  置信度: {conf:.4f}  |  "
                f"扎根度: {comps.get('grounding', '—'):.3f}  |  "
                f"多样性: {comps.get('support_diversity', '—'):.3f}  |  "
                f"稳定性: {comps.get('semantic_stability', '—'):.3f}  |  "
                f"溯源深度: {comps.get('provenance_depth', '—'):.3f}"
            )
            self.detail_label.setText(detail)


# ── Merge Provenance Tab ─────────────────────────────────────────

class MergeProvenanceTab(QWidget):
    """Display merge provenance (audit trail for hierarchy stabilization)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        info = QLabel("层级稳定化过程中的合并溯源记录，可审计每次合并操作。")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["类型", "详情", "涉及节点数"])
        self.tree.setColumnWidth(0, 120)
        self.tree.setColumnWidth(1, 500)
        self.tree.setColumnWidth(2, 100)
        layout.addWidget(self.tree)

    def load_data(self):
        try:
            with open(MERGE_PROVENANCE_PATH, "r", encoding="utf-8") as f:
                mp = json.load(f)
        except Exception:
            self.tree.clear()
            return

        self.tree.clear()

        # L2 merges
        l2_merges = mp.get("l2_merges", [])
        if l2_merges:
            l2_root = QTreeWidgetItem(self.tree, ["二阶合并", f"{len(l2_merges)} 次合并", ""])
            for m in l2_merges:
                source = m.get("merged_theme", "?")
                target = m.get("into_theme", "?")
                sim = m.get("similarity", 0)
                merge_type = m.get("type", "")
                item = QTreeWidgetItem(l2_root, [
                    "二阶合并",
                    f"{source} → {target}",
                    str(m.get("n_anchors", 1))
                ])
                QTreeWidgetItem(item, ["相似度", f"{sim:.4f}", ""])
                QTreeWidgetItem(item, ["类型", merge_type, ""])
            l2_root.setExpanded(True)

        # L3 merges
        l3_merges = mp.get("l3_merges", [])
        if l3_merges:
            l3_root = QTreeWidgetItem(self.tree, ["三阶合并", f"{len(l3_merges)} 个合并簇", ""])
            for cluster in l3_merges:
                canonical = cluster.get("canonical", "?")
                members = cluster.get("members", [])
                size = cluster.get("size", len(members))
                item = QTreeWidgetItem(l3_root, [
                    "三阶合并簇",
                    canonical,
                    str(size)
                ])
                for member in members:
                    QTreeWidgetItem(item, ["← 吸收", member, ""])
            l3_root.setExpanded(True)

        # Collisions
        collisions = mp.get("collision_fixes", [])
        if collisions:
            col_root = QTreeWidgetItem(self.tree, ["冲突修复", f"{len(collisions)} 处", ""])
            for c in collisions:
                desc = c.get("collision", c.get("description", str(c)))
                action = c.get("action", "")
                new_name = c.get("new_name", "")
                reason = c.get("reason", "")
                item = QTreeWidgetItem(col_root, ["冲突", desc, ""])
                QTreeWidgetItem(item, ["操作", action, ""])
                if new_name:
                    QTreeWidgetItem(item, ["新名称", new_name, ""])
                if reason:
                    QTreeWidgetItem(item, ["原因", reason, ""])
            col_root.setExpanded(True)

        # Re-mappings
        remaps = mp.get("re_mappings", [])
        if remaps:
            remap_root = QTreeWidgetItem(self.tree, ["重新映射", f"{len(remaps)} 个", ""])
            # Show first 50, summarize rest
            for r in remaps[:50]:
                anchor = r.get("anchor", "?")
                new_l2 = r.get("new_l2", "?")
                new_l3 = r.get("new_l3", "?")
                conf = r.get("new_confidence", 0)
                item = QTreeWidgetItem(remap_root, [
                    "重映射",
                    f"{anchor} → {new_l2} / {new_l3}",
                    ""
                ])
                QTreeWidgetItem(item, ["新置信度", f"{conf:.4f}", ""])
            if len(remaps) > 50:
                QTreeWidgetItem(remap_root, [
                    "...", f"还有 {len(remaps) - 50} 条", ""
                ])
            remap_root.setExpanded(False)


# ── Main Dashboard Dialog ────────────────────────────────────────

class GovernanceDashboard(QDialog):
    """Main governance dashboard dialog with tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("语义治理仪表盘 — Semantic Governance Dashboard")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 750)
        self._init_ui()
        self.load_all()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("扎根理论编码系统 — 交互式语义治理")
        header.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()

        self.overview_tab = OverviewTab()
        self.tabs.addTab(self.overview_tab, "总览")

        self.weak_nodes_tab = WeakNodesTab()
        self.tabs.addTab(self.weak_nodes_tab, "薄弱节点")

        self.network_tab = NetworkGraphTab()
        self.tabs.addTab(self.network_tab, "理论网络图")

        self.merge_tab = MergeProvenanceTab()
        self.tabs.addTab(self.merge_tab, "合并溯源")

        layout.addWidget(self.tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("刷新全部数据")
        refresh_btn.clicked.connect(self.load_all)
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def load_all(self):
        """Load all data into all tabs."""
        try:
            self.overview_tab.load_data()
            self.weak_nodes_tab.load_data()
            self.network_tab.load_data()
            self.merge_tab.load_data()
        except Exception as e:
            logger.error("Dashboard load failed: %s", e, exc_info=True)


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Test standalone
    dashboard = GovernanceDashboard()
    dashboard.show()
    sys.exit(app.exec_())
