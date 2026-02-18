"""Isolated test for Fix 1 + Fix 2 (no heavy imports)."""
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Tuple

# ============================================================================
# Copy of the relevant functions from doctor_graph.py (standalone)
# ============================================================================

def normalize_vietnamese_name(name: str) -> str:
    name = name.lower().strip()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    replacements = {'đ': 'd', 'Đ': 'D'}
    for old, new in replacements.items():
        name = name.replace(old, new)
    name = re.sub(r'\s+', ' ', name)
    return name

def extract_vietnamese_given_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[-1] if parts else ""

def fuzzy_match_score(name1: str, name2: str) -> float:
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    if n1 == n2:
        return 1.0
    n1_normalized = normalize_vietnamese_name(name1)
    n2_normalized = normalize_vietnamese_name(name2)
    if n1_normalized == n2_normalized:
        return 0.98
    given1 = extract_vietnamese_given_name(n1)
    given2 = extract_vietnamese_given_name(n2)
    given1_norm = normalize_vietnamese_name(given1)
    given2_norm = normalize_vietnamese_name(given2)
    given_names_match = (given1 == given2 or given1_norm == given2_norm)
    if n1 in n2 or n2 in n1:
        return 0.95 if given_names_match else 0.5
    if n1_normalized in n2_normalized or n2_normalized in n1_normalized:
        return 0.92 if given_names_match else 0.45
    base_score = SequenceMatcher(None, n1_normalized, n2_normalized).ratio()
    if not given_names_match:
        base_score *= 0.4
    return base_score

def find_best_patient_matches(
    search_name: str,
    patients: List[dict],
    min_score: float = 0.8
) -> List[Tuple[dict, float]]:
    matches = []
    exact_matches = []
    search_normalized = normalize_vietnamese_name(search_name)
    search_given = normalize_vietnamese_name(extract_vietnamese_given_name(search_name))
    is_given_name_only = len(search_name.strip().split()) == 1

    for patient in patients:
        full_name = patient.get("full_name", "")
        patient_normalized = normalize_vietnamese_name(full_name)
        patient_given = normalize_vietnamese_name(extract_vietnamese_given_name(full_name))

        if search_normalized == patient_normalized:
            exact_matches.append((patient, 1.0))
            continue

        if is_given_name_only and search_normalized == patient_given:
            exact_matches.append((patient, 0.95))
            continue

        score = fuzzy_match_score(search_name, full_name)
        if score >= min_score:
            matches.append((patient, score))

    if exact_matches:
        if len(exact_matches) == 1 and not is_given_name_only:
            return exact_matches
        exact_matches.sort(key=lambda x: x[1], reverse=True)
        return exact_matches

    matches.sort(key=lambda x: x[1], reverse=True)
    if len(matches) > 1:
        top_score = matches[0][1]
        matches = [(p, s) for p, s in matches if s >= top_score - 0.1]
    return matches


# ============================================================================
# FIX 1 TESTS: Vietnamese keyword separator
# ============================================================================
print("=" * 60)
print("FIX 1: Vietnamese keyword ': ' separator")
print("=" * 60)

KEYWORD_PATTERN = re.compile(
    r'((?:Đánh giá|Phân tích|Đề xuất|Cảnh báo|Lưu ý|Kết luận|Theo dõi|Khuyến nghị))'
    r'(?![\s:：\-])'
    r'([A-ZÀ-Ỵa-zà-ỵ])',
    re.UNICODE
)

tests_1 = [
    ('Đánh giáBệnh nhân Trần Thị Lan', 'Đánh giá: Bệnh nhân Trần Thị Lan'),
    ('Cảnh báoĐường huyết cao', 'Cảnh báo: Đường huyết cao'),
    ('Phân tíchKết quả xét nghiệm', 'Phân tích: Kết quả xét nghiệm'),
    ('Đánh giá: Bệnh nhân OK', 'Đánh giá: Bệnh nhân OK'),  # No change
    ('Cảnh báo- Đường huyết', 'Cảnh báo- Đường huyết'),     # No change (dash)
    ('Đề xuất điều trị', 'Đề xuất điều trị'),                # No change (space)
]

for input_text, expected in tests_1:
    result = KEYWORD_PATTERN.sub(r'\1: \2', input_text)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{input_text}' → '{result}'")
    assert result == expected, f"FAIL: expected '{expected}', got '{result}'"

print()

# ============================================================================
# FIX 2 TESTS: Patient disambiguation
# ============================================================================
print("=" * 60)
print("FIX 2: Patient disambiguation")
print("=" * 60)

patients = [
    {'id': '1', 'full_name': 'Nguyễn Thị Lan', 'primary_diagnosis': 'E11'},
    {'id': '2', 'full_name': 'Phạm Mai Lan', 'primary_diagnosis': 'I10'},
    {'id': '3', 'full_name': 'Trần Văn Bình', 'primary_diagnosis': 'E11'},
]

# Test: "Lan" → both Lans
results = find_best_patient_matches('Lan', patients)
print(f"\n  Search 'Lan': {len(results)} matches")
for p, s in results:
    print(f"    - {p['full_name']} (score={s})")
assert len(results) == 2
names = {p['full_name'] for p, _ in results}
assert 'Nguyễn Thị Lan' in names and 'Phạm Mai Lan' in names
print("  ✅ Both Lan patients found\n")

# Test: Full name → single result
results2 = find_best_patient_matches('Nguyễn Thị Lan', patients)
print(f"  Search 'Nguyễn Thị Lan': {len(results2)} matches")
assert len(results2) == 1 and results2[0][0]['full_name'] == 'Nguyễn Thị Lan'
print("  ✅ Full name → single result\n")

# Test: Unique given name → single
results3 = find_best_patient_matches('Bình', patients)
print(f"  Search 'Bình': {len(results3)} matches")
assert len(results3) == 1 and results3[0][0]['full_name'] == 'Trần Văn Bình'
print("  ✅ Unique given name → single result\n")

print("=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)
