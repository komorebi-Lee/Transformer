#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建一个简单的测试PDF文件，用于测试PDF表格提取功能
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# 创建PDF文件
c = canvas.Canvas('test_table.pdf', pagesize=letter)
width, height = letter

# 添加标题
c.setFont('Helvetica-Bold', 16)
c.drawString(100, height - 50, '测试PDF表格')

# 准备表格数据
data = [
    ['姓名', '年龄', '性别', '职业'],
    ['张三', '25', '男', '工程师'],
    ['李四', '30', '女', '教师'],
    ['王五', '35', '男', '医生'],
    ['赵六', '28', '女', '设计师']
]

# 创建表格
table = Table(data, colWidths=[100, 60, 60, 120])

# 设置表格样式
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))

# 绘制表格
table.wrapOn(c, width, height)
table.drawOn(c, 100, height - 200)

# 保存PDF文件
c.save()
print("测试PDF文件创建成功: test_table.pdf")
