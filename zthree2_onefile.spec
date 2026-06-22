# -*- mode: python ; coding: utf-8 -*-
"""
扎根理论编码系统 - 单文件打包配置 (onefile)
排除模型文件，仅打包代码和必要依赖
"""
import sys
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

project_root = os.path.abspath(SPECPATH)

# 收集需要的数据文件（仅 Python 代码和少量配置）
datas = []

# 只收集 .py 文件，不收集模型文件
for root, dirs, files in os.walk(project_root):
    # 排除不需要的目录
    dirs[:] = [d for d in dirs if d not in [
        '__pycache__', 'build', 'dist', '.git', '.idea', 
        'venv', 'env', 'local_models', 'trained_models',
        'standard_answers', 'node_modules', '.vscode', '.trae'
    ]]
    for file in files:
        if file.endswith('.py'):
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_root)
            target_dir = os.path.dirname(rel_path)
            datas.append((full_path, target_dir if target_dir else '.'))

# 隐藏导入（仅项目实际使用的模块）
hiddenimports = [
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    'PyQt5.QtPrintSupport',
    
    # 数据处理
    'numpy',
    'numpy.core._multiarray_umath',
    'numpy.linalg.lapack_lite',
    'pandas',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.np_datetime',
    
    # 深度学习 - PyTorch
    'torch',
    'torch._C',
    'torch.nn',
    'torch.nn.functional',
    'torch.optim',
    'torch.utils.data',
    'torch.utils.data.dataloader',
    'torch.serialization',
    'torch.jit',
    'torch.jit._script',
    'torch.backends',
    'torch.backends.cudnn',
    'torch.backends.mkldnn',
    'torch.backends.openmp',
    'torch.backends.mps',
    
    # Transformers
    'transformers',
    'transformers.models.bert',
    'transformers.models.bert.tokenization_bert',
    'transformers.models.bert.tokenization_bert_fast',
    'transformers.models.bert.modeling_bert',
    'transformers.modeling_utils',
    'transformers.configuration_utils',
    'transformers.tokenization_utils',
    'transformers.tokenization_utils_base',
    'transformers.tokenization_utils_fast',
    'transformers.trainer',
    'transformers.training_args',
    'transformers.integrations',
    'transformers.data',
    'transformers.pipelines',
    'transformers.optimization',
    'transformers.file_utils',
    'transformers.utils',
    'transformers.deepspeed',
    
    # Sentence Transformers
    'sentence_transformers',
    'sentence_transformers.models',
    'sentence_transformers.losses',
    'sentence_transformers.util',
    
    # HuggingFace生态
    'huggingface_hub',
    'huggingface_hub.file_download',
    'accelerate',
    'accelerate.utils',
    'accelerate.state',
    'safetensors',
    'safetensors.torch',
    'tokenizers',
    'tokenizers.models',
    'tokenizers.trainers',
    'tokenizers.pre_tokenizers',
    'tokenizers.decoders',
    'tokenizers.processors',
    'tokenizers.normalizers',
    
    # 机器学习（仅实际使用的子模块）
    'sklearn',
    'sklearn.base',
    'sklearn.utils',
    'sklearn.utils.validation',
    'sklearn.metrics',
    'sklearn.metrics.pairwise',
    'sklearn.model_selection',
    'sklearn.model_selection._split',
    'sklearn.neighbors',
    'sklearn.preprocessing',
    'sklearn.ensemble',
    'sklearn.tree',
    'sklearn.pipeline',
    'sklearn.compose',
    
    # scipy（sklearn依赖的核心部分）
    'scipy',
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.linalg',
    'scipy.linalg',
    'scipy.stats',
    'scipy.special',
    'scipy.optimize',
    'scipy.integrate',
    'scipy.spatial',
    'scipy.spatial.distance',
    'scipy.cluster',
    'scipy.ndimage',
    'scipy.fft',
    'scipy.signal',
    
    # 其他依赖
    'jieba',
    'jieba.posseg',
    'jieba.analyse',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
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
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.reader',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.descriptors',
    'openpyxl.xml',
    'et_xmlfile',
    'requests',
    'requests.adapters',
    'urllib3',
    'urllib3.util',
    'charset_normalizer',
    'certifi',
    'idna',
    'pyarrow',
    'pyarrow.types',
    'regex',
    'packaging',
    'packaging.version',
    'filelock',
    'fsspec',
    'fsspec.implementations',
    'yaml',
    'tqdm',
    'tqdm.auto',
    'psutil',
    'joblib',
    'threadpoolctl',
    'typing_extensions',
    'dateutil',
    'dateutil.parser',
    'dateutil.tz',
    'pytz',
    'six',
    'ctypes.wintypes',
    'pdb',
    
    # 项目内部模块
    'app_launcher',
    'main_window',
    'workspace_page',
    'path_manager',
    'config',
    'model_manager',
    'data_processor',
    'enhanced_coding_generator',
    'standard_answer_manager',
    'training_manager',
    'text_navigator',
    'grounded_theory_coder',
    'word_exporter',
    'model_downloader',
    'manual_coding_dialog',
    'project_manager',
    'bert_finetuner',
    'bert_dataset',
    'hyperparameter_optimizer',
    'excel_processor',
    'text_numbering',
    'code_validator',
    'rag_index',
    'coding_library_manager',
    'rag_doc_retriever',
    'semantic_matcher',
    'server_model',
    'provenance_store',
    'explainability',
    'theory_evidence',
    'theory_network',
]

# 排除的模块
excludes = [
    # 开发工具
    'IPython',
    'jupyter',
    'notebook',
    'qtconsole',
    'spyder',
    'spyder_kernels',
    'pylint',
    'pyflakes',
    'mypy',
    'black',
    'isort',
    'flake8',
    'pytest',
    'unittest.mock',
    'pdbpp',
    'ipdb',
    
    # GUI框架（使用PyQt5）
    'tkinter',
    'Tkinter',
    '_tkinter',
    'turtle',
    'turtledemo',
    'idlelib',
    
    # 可视化
    'matplotlib',
    'PIL',
    'Pillow',
    
    # 文档工具
    'sphinx',
    'docutils',
    'pydoc',
    'pydoc_data',
    
    # 包管理
    'pip',
    'ensurepip',
    'venv',
    'virtualenv',
    'wheel',
    'twine',
    'distutils',
    'setuptools._distutils',
    
    # 测试模块
    'test',
    'tests',
    '_testcapi',
    '_testinternalcapi',
    '_testbuffer',
    '_testimportmultiple',
    '_testmultiphase',
    '_testconsole',
    'unittest.test',
    
    # 不需要的科学计算库
    'sympy',
    'mpmath',
    'networkx',
    'numexpr',
    'Bottleneck',
    
    # 其他不需要的模块
    'wsgiref',
    'curses',
    'multiprocessing.tests',
    'concurrent.futures.tests',
    'email.test',
    'json.tests',
    'lib2to3.tests',
    'sqlite3.test',
    'xml.etree.tests',
    'xml.dom.tests',
    'xml.sax.tests',
    'html.tests',
    'http.tests',
    'urllib.tests',
    'ctypes.test',
    'distutils.tests',
    'logging.tests',
    'jinja2.debug',
    'jinja2.asyncsupport',
    'asyncio.test_utils',
    
    # torchvision/torchaudio（未使用）
    'torchvision',
    'torchaudio',
    
    # ONNX（未使用）
    'torch.onnx',
]

# 分析配置
a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# 创建 PYZ
pyz = PYZ(a.pure, a.zipped_data)

# 创建单文件 EXE (onefile)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zthree2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台以便查看错误
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
