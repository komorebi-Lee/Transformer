# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob

# 项目根目录
project_root = os.path.abspath(SPECPATH)

# ============================================================================
# 模型文件 — 仅包含运行时实际需要的最小集合
# ============================================================================
REQUIRED_MODELS = [
    "local_models/custom_bert_4layer",
    "trained_models/abstract_reranker_latest",
    "trained_models/concept_anchor_v6",
    "local_models/chinese_t5_pegasus_base",  # FAISS 弱匹配时 T5 补充生成
    "trained_models/t5_lora_coding",         # T5 LoRA 权重
]

model_files = []
for model_rel in REQUIRED_MODELS:
    model_abs = os.path.join(project_root, model_rel)
    if os.path.exists(model_abs):
        for root, dirs, files in os.walk(model_abs):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)
                model_files.append((full_path, rel_path))

# ============================================================================
# 数据文件（全部进入 _internal/，onedir 持久不丢失）
# ============================================================================
datas = []

for full_path, rel_path in model_files:
    target_dir = os.path.dirname(rel_path)
    datas.append((full_path, target_dir) if target_dir else (full_path, '.'))

coding_library = os.path.join(project_root, 'coding_library.json')
if os.path.exists(coding_library):
    datas.append((coding_library, '.'))

data_dir = os.path.join(project_root, 'data')
if os.path.exists(data_dir):
    for fname in os.listdir(data_dir):
        if fname.endswith('.json'):
            full = os.path.join(data_dir, fname)
            if os.path.isfile(full):
                datas.append((full, 'data'))

cache_anchor_dir = os.path.join(project_root, 'cache', 'anchor_index')
if os.path.exists(cache_anchor_dir):
    for fname in os.listdir(cache_anchor_dir):
        if fname.endswith(('.faiss', '.json')):
            full = os.path.join(cache_anchor_dir, fname)
            if os.path.isfile(full):
                datas.append((full, 'cache/anchor_index'))

# 添加 regex 包的元数据文件
import regex
regex_path = os.path.dirname(regex.__file__)
regex_metadata = os.path.join(regex_path, '..', 'regex-*.dist-info')
regex_metadata_files = glob.glob(regex_metadata)
for metadata_file in regex_metadata_files:
    if os.path.exists(metadata_file):
        target_dir = os.path.basename(metadata_file)
        datas.append((metadata_file, target_dir))

# 添加 transformers 包的元数据文件
import transformers
transformers_path = os.path.dirname(transformers.__file__)
transformers_metadata = os.path.join(transformers_path, '..', 'transformers-*.dist-info')
transformers_metadata_files = glob.glob(transformers_metadata)
for metadata_file in transformers_metadata_files:
    if os.path.exists(metadata_file):
        target_dir = os.path.basename(metadata_file)
        datas.append((metadata_file, target_dir))

excludes = []

# ============================================================================
# 隐藏导入
# ============================================================================
hiddenimports = [
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',

    # 数据处理
    'pandas',
    'pandas._libs.tslibs',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.offsets',
    'pandas._libs.tslibs.timestamps',
    'pandas._libs.tslibs.timezones',
    'numpy',
    'numpy.core',
    'numpy.core._dtype_ctypes',
    'numpy.core._multiarray_umath',
    'numpy.linalg.lapack_lite',

    # Excel 处理
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.chart',
    'openpyxl.comments',
    'openpyxl.compat',
    'openpyxl.descriptors',
    'openpyxl.drawing',
    'openpyxl.formatting',
    'openpyxl.formula',
    'openpyxl.packaging',
    'openpyxl.pivot',
    'openpyxl.reader',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.writer',
    'openpyxl.xml',
    'et_xmlfile',

    # Word 处理
    'docx',
    'docx.api',
    'docx.document',
    'docx.opc',
    'docx.oxml',
    'docx.parts',
    'docx.section',
    'docx.settings',
    'docx.shared',
    'docx.styles',
    'docx.table',
    'docx.text',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',

    # 深度学习
    'torch',
    'torch.nn',
    'torch.nn.functional',
    'torch.optim',
    'torch.utils',
    'torch.utils.data',
    'torch.serialization',
    'torch.jit',

    # Transformers
    'transformers',
    'transformers.models',
    'transformers.models.bert',
    'transformers.models.bert.tokenization_bert',
    'transformers.models.bert.tokenization_bert_fast',
    'transformers.models.bert.modeling_bert',
    'transformers.tokenization_utils',
    'transformers.tokenization_utils_base',
    'transformers.tokenization_utils_fast',
    'transformers.modeling_utils',
    'transformers.configuration_utils',
    'transformers.file_utils',
    'transformers.utils',
    'transformers.pipelines',
    'transformers.data',
    'transformers.trainer',
    'transformers.training_args',
    'transformers.integrations',

    # Sentence Transformers
    'sentence_transformers',
    'sentence_transformers.models',
    'sentence_transformers.losses',
    'sentence_transformers.evaluation',
    'sentence_transformers.datasets',
    'sentence_transformers.util',

    # 其他依赖
    'jieba',
    'requests',
    'urllib3',
    'charset_normalizer',
    'certifi',
    'idna',
    'huggingface_hub',
    'huggingface_hub.commands',
    'accelerate',
    'accelerate.commands',
    'safetensors',
    'safetensors.torch',
    'tokenizers',
    'tokenizers.models',
    'tokenizers.trainers',
    'tokenizers.pre_tokenizers',
    'tokenizers.decoders',
    'tokenizers.processors',
    'tokenizers.normalizers',
    'tokenizers.implementations',
    'regex',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
    'filelock',
    'fsspec',
    'fsspec.implementations',
    'yaml',
    'tqdm',
    'tqdm.auto',
    'tqdm.notebook',
    'psutil',
    'psutil._psutil_windows',

    # 机器学习
    'sklearn',
    'sklearn.base',
    'sklearn.utils',
    'sklearn.utils._joblib',
    'sklearn.utils.validation',
    'sklearn.preprocessing',
    'sklearn.feature_extraction',
    'sklearn.feature_extraction.text',
    'sklearn.decomposition',
    'sklearn.cluster',
    'sklearn.metrics',
    'sklearn.metrics.pairwise',
    'sklearn.model_selection',
    'sklearn.linear_model',
    'sklearn.svm',
    'sklearn.ensemble',
    'sklearn.tree',
    'sklearn.neighbors',
    'sklearn.naive_bayes',
    'sklearn.discriminant_analysis',
    'sklearn.calibration',
    'sklearn.neural_network',
    'sklearn.pipeline',
    'sklearn.compose',
    'sklearn.impute',
    'sklearn.experimental',
    'sklearn.manifold',
    'sklearn.semi_supervised',
    'sklearn.covariance',
    'sklearn.random_projection',
    'sklearn.kernel_approximation',
    'sklearn.multioutput',
    'sklearn.multiclass',
    'sklearn.dummy',
    'sklearn.isotonic',
    'sklearn.cross_decomposition',
    'sklearn.gaussian_process',
    'sklearn.mixture',
    'sklearn.model_selection',
    'sklearn.inspection',
    'sklearn._config',
    'sklearn.__check_build',
    'sklearn._distributor_init',
    'scipy',
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.linalg',
    'scipy.linalg',
    'scipy.stats',
    'scipy.special',
    'scipy.integrate',
    'scipy.optimize',
    'scipy.interpolate',
    'scipy.fft',
    'scipy.signal',
    'scipy.ndimage',
    'scipy.spatial',
    'scipy.cluster',
    'joblib',
    'threadpoolctl',

    # 其他工具
    'typing_extensions',
    'annotated_types',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.ImageOps',
    'PIL.ImageChops',
    'PIL.ImagePalette',
    'PIL.ImageSequence',
    'PIL.ImageTk',
    'PIL.ImageWin',
    'PIL._imaging',
    'PIL._imagingft',
    'PIL._imagingtk',
    'PIL.features',
    'click',
    'colorama',
    'colorama.initialise',
    'colorama.ansi',
    'colorama.winterm',
    'colorama.win32',
    'dateutil',
    'dateutil.parser',
    'dateutil.tz',
    'dateutil.zoneinfo',
    'dateutil.rrule',
    'dateutil.easter',
    'dateutil.relativedelta',
    'pytz',
    'six',

    # 项目内部模块
    'path_manager',
    'config',
    'app_launcher',
    'main_window',
    'manual_coding_dialog',
    'standard_answer_manager',
    'excel_processor',
    'grounded_theory_coder',
    'enhanced_coding_generator',
    'project_manager',
    'model_manager',
    'text_numbering',
    'data_processor',
    'word_table_importer',
    'word_exporter',
    'training_manager',
    'text_navigator',
    'server_model',
    'model_downloader',
    'enhanced_word_exporter',
    'download_models',

    # 额外的依赖
    'importlib_metadata',
    'importlib_resources',
    'zipp',
    'tomli',
    'pyarrow',
    'pyarrow.lib',
    'pyarrow._compute',
    'pyarrow._csv',
    'pyarrow._dataset',
    'pyarrow._flight',
    'pyarrow._hdfs',
    'pyarrow._json',
    'pyarrow._orc',
    'pyarrow._parquet',
    'pyarrow._plasma',
    'pyarrow._s3fs',
    'pyarrow._util',
    'pyarrow.compat',
    'pyarrow.compute',
    'pyarrow.csv',
    'pyarrow.dataset',
    'pyarrow.flight',
    'pyarrow.fs',
    'pyarrow.hdfs',
    'pyarrow.json',
    'pyarrow.orc',
    'pyarrow.parquet',
    'pyarrow.plasma',
    'pyarrow.serialization',
    'pyarrow.types',
    'pyarrow.utf8',
    'regex._regex',
    'regex._regex_core',
    'regex.regex',
]

# ============================================================================
# 分析配置
# ============================================================================
a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 创建 PYZ
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建 EXE（onedir 多文件模式，启动快、数据持久化）
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='zthree2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='zthree2',
)
