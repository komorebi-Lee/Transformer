def update_structured_codes_from_tree(self):
    """从树形结构更新编码数据"""
    self.current_codes = {}
    self.unclassified_first_codes = []

    for i in range(self.coding_tree.topLevelItemCount()):
        top_item = self.coding_tree.topLevelItem(i)
        item_data = top_item.data(0, Qt.UserRole)

        if not item_data:
            continue

        level = item_data.get("level")

        if level == 3:
            # 三阶编码
            third_display_name = top_item.text(0)
            # 解析显示名称，获取原始名称（去掉编号）
            import re
            third_parts = third_display_name.split(' ', 1)
            if len(third_parts) > 1 and re.match(r'^[A-Z]\d{2}$', third_parts[0]):
                third_name = third_parts[1]
            else:
                third_name = third_display_name

            self.current_codes[third_display_name] = {}

            for j in range(top_item.childCount()):
                second_item = top_item.child(j)
                second_display_name = second_item.text(0)
                # 解析二阶编码名称，获取原始名称（去掉编号）
                import re
                second_parts = second_display_name.split(' ', 1)
                if len(second_parts) > 1 and re.match(r'^[A-Z]\d{2}$', second_parts[0]):
                    second_name = second_parts[1]
                else:
                    second_name = second_display_name

                self.current_codes[third_display_name][second_display_name] = []

                for k in range(second_item.childCount()):
                    first_item = second_item.child(k)
                    # 获取原始内容，优先使用完整数据结构
                    first_item_data = first_item.data(0, Qt.UserRole)

                    # 正确处理三阶-二阶-一阶结构中的一阶编码
                    if first_item_data and isinstance(first_item_data, dict):
                        # 更新一阶编码的统计数据
                        first_item_data["sentence_count"] = int(first_item.text(4)) if first_item.text(
                            4).isdigit() else 1
                        first_item_data["code_id"] = first_item.text(5) if first_item.text(
                            5) else first_item_data.get("code_id", "")
                        # 修复：应该添加到正确的嵌套结构中，而不是未分类编码
                        self.current_codes[third_display_name][second_display_name].append(first_item_data)
                    else:
                        # 后备方案：使用文本内容
                        first_content = first_item.text(0)
                        self.current_codes[third_display_name][second_display_name].append(first_content)

        elif level == 1:
            # 未分类的一阶编码
            if not item_data.get("classified", True):
                # 尝试获取完整数据结构，否则使用文本内容
                if isinstance(item_data, dict):
                    # 更新未分类一阶编码的统计数据
                    item_data["sentence_count"] = int(top_item.text(4)) if top_item.text(4).isdigit() else 1
                    item_data["code_id"] = top_item.text(5) if top_item.text(5) else item_data.get("code_id", "")
                    self.unclassified_first_codes.append(item_data)
                else:
                    content = top_item.text(0)
                    self.unclassified_first_codes.append(content)

    # 调试输出
    print(f"DEBUG: 更新后 current_codes 结构:")
    for third_cat, second_cats in self.current_codes.items():
        print(f"  {third_cat}: {len(second_cats)} 个二阶编码")
        for second_cat, first_contents in second_cats.items():
            print(f"    {second_cat}: {len(first_contents)} 个一阶编码")
    print(f"DEBUG: 未分类一阶编码: {len(self.unclassified_first_codes)} 个")
