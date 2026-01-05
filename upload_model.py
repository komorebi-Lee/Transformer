from huggingface_hub import HfApi, upload_folder

# 替换为你的信息
HF_TOKEN = "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"
REPO_ID = "lily-liuqian/zthree2"  # 仓库ID（用户名/仓库名）
LOCAL_FOLDER = "D:/zthree2"  # 本地模型文件所在目录

# 初始化API并上传整个文件夹
api = HfApi(token=HF_TOKEN)
api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id=REPO_ID,
    repo_type="model",  # 存储大模型选model，数据集选dataset
    ignore_patterns=[".git", "*.log"],  # 忽略无关文件
)
print("上传完成！")