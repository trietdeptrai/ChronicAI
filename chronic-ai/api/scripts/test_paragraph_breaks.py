"""Standalone test for _add_paragraph_breaks function."""
import re


def _add_paragraph_breaks(text: str) -> str:
    """
    Add line breaks to dense Vietnamese text for better readability.

    Strategy: split into sentences, then insert blank lines at topic
    boundaries (bullet points, questions, transitional phrases, and
    after long runs of text).

    Args:
        text: Dense text without proper formatting

    Returns:
        Text with paragraph breaks inserted
    """
    if not text or len(text) < 100:
        return text

    # If the text already has reasonable formatting, leave it alone
    if text.count("\n\n") >= 3:
        return text

    # ---- Step 1: Normalize inline markdown and list markers ----
    # Handle inline markdown headers: "...ổn định.## Phân tích" → split before ##
    text = re.sub(r'(?<!\n)(#{1,4}\s)', r'\n\n\1', text)
    # Handle inline dash lists: "...huyết áp.- Điều trị:" → split before dash
    text = re.sub(r'([.!?])\s*-\s+', r'\1\n\n- ', text)
    # Handle "...thương.•Suy hô hấp" → split before bullet
    text = re.sub(r'([.!?])\s*([•●▪]\s*)', r'\1\n\n\2', text)
    # Handle "...thương.1. Suy hô hấp" → split before numbered list
    text = re.sub(r'([.!?])\s*(\\d+[.)]\s)', r'\1\n\n\2', text)

    # ---- Step 2: Split into lines (preserve any existing breaks) ----
    lines = text.split("\n")
    result_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            result_lines.append("")
            continue

        # If the line is short enough, keep as-is
        if len(line) < 150:
            result_lines.append(line)
            continue

        # ---- Step 3: Split dense line into sentences ----
        # Split on sentence-ending punctuation followed by a space or bullet
        sentences = re.split(r'(?<=[.!?])\s+', line)

        current_paragraph: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Detect if this sentence starts a new topic
            is_new_topic = False

            # Bullet point or numbered list
            if re.match(r'^[•●▪\-]\s', sentence) or re.match(r'^\d+[.)]\s', sentence):
                is_new_topic = True

            # Question sentence
            elif sentence.endswith("?"):
                is_new_topic = True

            # Starts with a transitional/topic phrase
            elif re.match(
                r'^(Tuy nhiên|Ngoài ra|Vậy|Tóm lại|Điều này|Cách tiếp cận|'
                r'Lưu ý|Ví dụ|Về cơ bản|Nói chung|Cần lưu ý|Cần theo dõi|'
                r'Những điều|Việc điều trị|Do đó|Vì vậy|Bên cạnh đó|'
                r'However|In addition|Therefore|For example|In summary)',
                sentence, re.IGNORECASE
            ):
                is_new_topic = True

            # Current paragraph is getting long (>250 chars)
            elif current_length > 250:
                is_new_topic = True

            if is_new_topic and current_paragraph:
                # Flush current paragraph
                result_lines.append(" ".join(current_paragraph))
                result_lines.append("")  # blank line = paragraph break
                current_paragraph = []
                current_length = 0

            current_paragraph.append(sentence)
            current_length += len(sentence) + 1

        # Flush remaining sentences
        if current_paragraph:
            result_lines.append(" ".join(current_paragraph))

    # ---- Step 4: Clean up multiple blank lines ----
    cleaned: list[str] = []
    prev_blank = False
    for line in result_lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue  # skip double blanks
        cleaned.append(line)
        prev_blank = is_blank

    # Remove trailing blank line
    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()

    return "\n".join(cleaned)


# ============================================================================
# TEST 1: General query (bullet points)
# ============================================================================
print("=" * 60)
print("TEST 1: General query with inline bullets")
print("=" * 60)

test_general = (
    "Chào đồng nghiệp,Metformin là một thuốc điều trị tiểu đường type 2 rất phổ biến. "
    "Về tác dụng phụ, nó thường được dung nạp tốt, nhưng vẫn có một số tác dụng phụ cần lưu ý."
    "Tác dụng phụ thường gặp nhất:•Rối loạn tiêu hóa: Đây là tác dụng phụ phổ biến nhất, "
    "đặc biệt khi mới bắt đầu dùng thuốc.•Buồn nôn•Nôn mửa•Tiêu chảy•Đau bụng•Chán ăn"
    "Hy vọng thông tin này hữu ích cho bạn."
)

result = _add_paragraph_breaks(test_general)
print(result)
print(f"\n--- Paragraph breaks: {result.count(chr(10) + chr(10))} ---\n")

# ============================================================================
# TEST 2: Patient-specific query (inline ## headers) — the broken case!
# ============================================================================
print("=" * 60)
print("TEST 2: Patient-specific query with inline ## headers")
print("=" * 60)

test_patient = (
    "Đánh giáBệnh nhân Trần Thị Bình, 61 tuổi, có tiền sử Đái tháo đường type 2 (E11) "
    "và Tăng huyết áp (I10). Bệnh nhân đang dùng Metformin 500mg 2 lần/ngày và Amlodipine "
    "5mg 1 lần/ngày. Tình trạng bệnh được ghi nhận là ổn định, tuân thủ điều trị tốt, "
    "không có triệu chứng hạ đường huyết. Kết quả xét nghiệm máu gần đây (15/12/2024) "
    "cho thấy đường huyết lúc đói hơi cao (7.2 mmol/L). Sinh hiệu gần đây cho thấy "
    "huyết áp dao động trong khoảng 135/85 mmHg đến 145/94 mmHg, nhịp tim dao động "
    "72-80 bpm, SpO2 ổn định ở 97-98%.## Phân tích- Đái tháo đường: Đường huyết lúc "
    "đói gần đây (7.2 mmol/L) vượt ngưỡng bình thường (3.9-6.1 mmol/L), cho thấy kiểm "
    "soát đường huyết có thể chưa đạt tới mục đích được ghi nhận là \"kiểm soát tốt\". "
    "Cần theo dõi HbA1c để đánh giá kiểm soát đường huyết trung bình.- Tăng huyết áp: "
    "Huyết áp dao động, có những lần vượt ngưỡng lý tưởng cho bệnh nhân đái tháo đường "
    "(thường là <130/80 mmHg), đặc biệt là huyết áp tâm thu (140-145 mmHg).## Đề xuất- "
    "Tiếp tục theo dõi đường huyết lúc đói và HbA1c để đánh giá hiệu quả kiểm soát "
    "đường huyết.- Cân nhắc điều chỉnh liều Metformin hoặc thêm thuốc hạ đường huyết "
    "khác nếu HbA1c không đạt mục tiêu.- Tiếp tục theo dõi huyết áp.- Cân nhắc điều "
    "chỉnh liều Amlodipine hoặc thêm thuốc hạ huyết áp khác nếu huyết áp thường xuyên "
    "vượt quá 130/80 mmHg.## Cảnh báo- Đường huyết lúc đói hơi cao, cần theo dõi sát "
    "HbA1c.- Huyết áp dao động và có những lần vượt ngưỡng mục tiêu, cần theo dõi sát "
    "và có thể cần điều chỉnh thuốc."
)

result2 = _add_paragraph_breaks(test_patient)
print(result2)
print(f"\n--- Paragraph breaks: {result2.count(chr(10) + chr(10))} ---")

# ============================================================================
# Assertions
# ============================================================================
print("\n" + "=" * 60)
print("VALIDATION")
print("=" * 60)

# Check that ## headers are on their own lines (preceded by blank line)
has_proper_headers = "\n\n## " in result2
print(f"✓ ## headers have preceding newline: {has_proper_headers}")
assert has_proper_headers, "FAIL: ## headers should have \\n\\n before them"

# Check that dash lists are split
has_dash_breaks = "\n\n- " in result2
print(f"✓ Dash lists have preceding newline: {has_dash_breaks}")
assert has_dash_breaks, "FAIL: Dash lists should have \\n\\n before them"

# Check that the text has at least a few paragraph breaks
break_count = result2.count("\n\n")
print(f"✓ Total paragraph breaks: {break_count}")
assert break_count >= 5, f"FAIL: Expected at least 5 paragraph breaks, got {break_count}"

print("\nAll checks passed! ✅")
