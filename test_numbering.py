# -*- coding: utf-8 -*-
from data_processor import DataProcessor

dp = DataProcessor()
text = '''您好，我们是华中科技大学管理学院的调研团队，目前正在做关于员工越轨创新行为的研究。本次访谈主要通过问答形式进行，访谈内容将严格保密，只做学术用途。本次访谈时间大概持续20-40分钟，为保证访谈的有效性，请根据您的真实经历或想法作答。十分感谢您的参与！先给您介绍以下越轨创新的定义与特征。创新通常是在组织或领导的安排下进行，员工根据计划完成创新任务。但在企业中也有一些员工在没有得到组织或领导的正式批准下，私下开展一些创新探索。例如，搜狐副总裁王小川当年力主开发搜狗浏览器，但遭到创始人张朝阳的反对。不过王小川并未放弃，而是将开发计划转到地下，最终取得成功。在学术上，这种现象被称为"越轨创新"，指创新想法产生之后，通过非常规手段来实现创新想法的具体过程。'''

numbered_text, mapping = dp.numbering_manager.number_text(text, 'test')
print('原始文本:')
print(text)
print('\n编号后文本:')
print(numbered_text)
print('\n编号映射:')
for num, sent in sorted(mapping.items()):
    print(f'[{num}] {sent}')