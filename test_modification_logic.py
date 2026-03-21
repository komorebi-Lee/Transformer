# Test script to reproduce modification detection issue
import copy
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StandardAnswerManagerMock:
    def _convert_to_standard_format(self, structured_codes):
        """Mock conversion to standard format without dependency on regex or self methods being exactly same"""
        standard_format = {}
        # Simplified conversion logic for mock
        if not structured_codes:
            return {}
            
        for third_cat, second_cats in structured_codes.items():
            standard_format[third_cat] = {}
            for second_cat, first_contents in second_cats.items():
                standard_format[third_cat][second_cat] = []
                for content in first_contents:
                    # Logic from actual manager:
                    if isinstance(content, dict):
                        # Ensure content field exists
                        if 'content' not in content and 'name' in content:
                            content['content'] = content['name']
                        standard_format[third_cat][second_cat].append(content)
                    else:
                        standard_format[third_cat][second_cat].append(str(content))
        return standard_format

    def _analyze_modifications(self, original, modified):
        """Analyze modifications logic from standard_answer_manager.py"""
        modifications = {
            "added": {},
            "modified": {},
            "deleted": {},
            "summary": {"added_codes": 0, "modified_codes": 0, "deleted_codes": 0},
            "has_changes": False
        }

        try:
            # Use mock conversion
            original_standard = self._convert_to_standard_format(original)
            modified_standard = self._convert_to_standard_format(modified)
            
            # 1. Check for Deleted Third Level Categories
            for third_cat in original_standard:
                if third_cat not in modified_standard:
                    print(f"Detected deleted third cat: {third_cat}")
                    modifications["deleted"][third_cat] = copy.deepcopy(original_standard[third_cat])
                    # Count codes in deleted category
                    count = 0 
                    for sc, fcs in original_standard[third_cat].items():
                         count += len(fcs)
                    modifications["summary"]["deleted_codes"] += count

            # 2. Check for Added Third Level Categories
            for third_cat in modified_standard:
                if third_cat not in original_standard:
                    modifications["added"][third_cat] = copy.deepcopy(modified_standard[third_cat])
                    # Count codes
                    count = 0
                    for sc, fcs in modified_standard[third_cat].items():
                        count += len(fcs)
                    modifications["summary"]["added_codes"] += count

            # 3. Check modifications within existing Third Level Categories
            for third_cat in modified_standard:
                if third_cat in original_standard:
                    third_modifications = self._analyze_second_level_modifications(
                        original_standard[third_cat],
                        modified_standard[third_cat]
                    )
                    
                    if third_modifications["has_changes"]:
                        modifications["modified"][third_cat] = third_modifications
                        modifications["summary"]["added_codes"] += third_modifications["summary"]["added_codes"]
                        modifications["summary"]["deleted_codes"] += third_modifications["summary"]["deleted_codes"]
                        modifications["summary"]["modified_codes"] += third_modifications["summary"]["modified_codes"]

            total_changes = (modifications["summary"]["added_codes"] + 
                             modifications["summary"]["deleted_codes"] +
                             modifications["summary"]["modified_codes"])
            modifications["has_changes"] = total_changes > 0

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            
        return modifications

    def _analyze_second_level_modifications(self, original_second, modified_second):
        """Analyze second level category changes"""
        modifications = {
            "added": {},
            "modified": {},
            "deleted": [],
            "summary": {"added_codes": 0, "modified_codes": 0, "deleted_codes": 0},
            "has_changes": False
        }
        
        # Check added second level
        for sec_cat in modified_second:
            if sec_cat not in original_second:
                modifications["added"][sec_cat] = copy.deepcopy(modified_second[sec_cat])
                modifications["summary"]["added_codes"] += len(modified_second[sec_cat])
        
        # Check deleted second level
        for sec_cat in original_second:
            if sec_cat not in modified_second:
                modifications["deleted"].append(sec_cat)
                modifications["summary"]["deleted_codes"] += len(original_second[sec_cat])

        # Check modified second level
        for sec_cat in modified_second:
            if sec_cat in original_second:
                first_modifications = self._analyze_first_level_modifications(
                    original_second[sec_cat],
                    modified_second[sec_cat]
                )
                
                if first_modifications["has_changes"]:
                    modifications["modified"][sec_cat] = first_modifications
                    modifications["summary"]["added_codes"] += first_modifications["summary"]["added_codes"]
                    modifications["summary"]["deleted_codes"] += first_modifications["summary"]["deleted_codes"]

        total = (modifications["summary"]["added_codes"] + 
                 modifications["summary"]["modified_codes"] + 
                 modifications["summary"]["deleted_codes"])
        modifications["has_changes"] = total > 0
        
        return modifications

    def _analyze_first_level_modifications(self, original_first, modified_first):
        """Analyze first level code changes"""
        modifications = {
            "added": [],
            "deleted": [],
            "summary": {"added_codes": 0, "deleted_codes": 0},
            "has_changes": False
        }

        # Helper to get unique key for comparison (content string)
        def get_content_key(item):
            if isinstance(item, dict):
                return item.get('content', item.get('name', str(item)))
            return str(item)

        # Build dict maps for fast lookup
        original_map = {get_content_key(item): item for item in original_first}
        modified_map = {get_content_key(item): item for item in modified_first}
        
        orig_keys = set(original_map.keys())
        mod_keys = set(modified_map.keys())
        
        # Identifty added
        added_keys = mod_keys - orig_keys
        if added_keys:
            modifications["added"] = [modified_map[k] for k in added_keys]
            modifications["summary"]["added_codes"] = len(added_keys)
            
        # Identify deleted
        deleted_keys = orig_keys - mod_keys
        if deleted_keys:
            print(f"  Found deleted keys: {deleted_keys}")
            modifications["deleted"] = [original_map[k] for k in deleted_keys]
            modifications["summary"]["deleted_codes"] = len(deleted_keys)
            
        modifications["has_changes"] = (len(added_keys) + len(deleted_keys)) > 0
        
        return modifications

# Test Case
def test_deletion_detection():
    manager = StandardAnswerManagerMock()
    
    # original state: 1 code
    original_data = {
        "Third1": {
            "Second1": [
                {"content": "FirstCode1", "id": 1},
                {"content": "FirstCode2", "id": 2}
            ]
        }
    }
    
    # modified state: FirstCode2 deleted
    modified_data = {
        "Third1": {
            "Second1": [
                {"content": "FirstCode1", "id": 1}
            ]
        }
    }
    
    print("Testing deletion of 1 code...")
    result = manager._analyze_modifications(original_data, modified_data)
    print(f"Has changes: {result['has_changes']}")
    print(f"Summary: {result['summary']}")
    
    if result["summary"]["deleted_codes"] == 1:
        print("PASS: Deletion detected correctly.")
    else:
        print("FAIL: Deletion not detected.")

if __name__ == "__main__":
    test_deletion_detection()
