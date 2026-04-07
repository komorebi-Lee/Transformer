import os
import csv
import json

# 定义编码库编码文件夹路径
coding_folder = "d:\\zthree2\\新增编码库编码"

# 存储提取的编码关系数据
coding_data = []

# 遍历所有CSV文件
for filename in os.listdir(coding_folder):
    if filename.endswith('.csv'):
        file_path = os.path.join(coding_folder, filename)
        print(f"处理文件: {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # 识别表头和数据区域
            i = 0
            while i < len(rows):
                row = rows[i]
                # 跳过空行
                if not any(row):
                    i += 1
                    continue
                
                # 检查是否是表头行
                header = row
                if '一阶' in str(header) and '二阶' in str(header) and ('三阶' in str(header) or '聚合' in str(header)):
                    # 识别列索引
                    first_order_idx = None
                    second_order_idx = None
                    third_order_idx = None
                    
                    for j, col in enumerate(header):
                        if '一阶' in col:
                            first_order_idx = j
                        elif '二阶' in col:
                            second_order_idx = j
                        elif '三阶' in col or '聚合' in col:
                            third_order_idx = j
                    
                    if first_order_idx is not None and second_order_idx is not None and third_order_idx is not None:
                        # 读取数据行
                        i += 1
                        while i < len(rows):
                            data_row = rows[i]
                            if not any(data_row):
                                i += 1
                                continue
                            # 检查是否是新的表头
                            if '一阶' in str(data_row) or '二阶' in str(data_row) or '三阶' in str(data_row) or '聚合' in str(data_row):
                                break
                            # 提取数据
                            if len(data_row) > max(first_order_idx, second_order_idx, third_order_idx):
                                first_order = data_row[first_order_idx].strip()
                                second_order = data_row[second_order_idx].strip()
                                third_order = data_row[third_order_idx].strip()
                                
                                if first_order and second_order and third_order:
                                    coding_data.append({
                                        'first_order': first_order,
                                        'second_order': second_order,
                                        'third_order': third_order
                                    })
                            i += 1
                else:
                    i += 1

# 保存提取的数据
with open('extracted_coding_data.json', 'w', encoding='utf-8') as f:
    json.dump(coding_data, f, ensure_ascii=False, indent=2)

print(f"提取完成，共提取 {len(coding_data)} 条编码关系数据")
