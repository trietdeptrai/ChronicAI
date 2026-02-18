"""
Regression tests for doctor graph formatting and patient disambiguation.
"""
import pytest

from app.services import doctor_graph


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakePatientsQuery:
    def __init__(self, patients):
        self._patients = patients
        self._pattern = None

    def select(self, *_args, **_kwargs):
        return self

    def ilike(self, _field, pattern):
        self._pattern = pattern
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._pattern:
            needle = self._pattern.strip("%").lower()
            data = [p for p in self._patients if needle in p["full_name"].lower()]
            return _FakeResponse(data)
        return _FakeResponse(self._patients)


class _FakeSupabase:
    def __init__(self, patients):
        self._patients = patients

    def table(self, _name):
        return _FakePatientsQuery(self._patients)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Đánh giáBệnh nhân Lan ổn định. Cần tiếp tục theo dõi đường huyết lúc đói định kỳ mỗi tuần để đảm bảo kiểm soát tốt.",
            "Đánh giá: Bệnh nhân Lan ổn định. Cần tiếp tục theo dõi đường huyết lúc đói định kỳ mỗi tuần để đảm bảo kiểm soát tốt.",
        ),
        (
            "Phân tích*Tăng huyết áp chưa kiểm soát. Huyết áp dao động nhiều trong tuần qua và cần đánh giá lại phác đồ điều trị hiện tại.",
            "Phân tích : Tăng huyết áp chưa kiểm soát. Huyết áp dao động nhiều trong tuần qua và cần đánh giá lại phác đồ điều trị hiện tại.",
        ),
        (
            "Đề xuất1. Điều chỉnh thuốc. Đồng thời tăng cường theo dõi chỉ số sinh hiệu và hẹn tái khám trong vòng hai tuần tới.",
            "Đề xuất:\n\n1. Điều chỉnh thuốc. Đồng thời tăng cường theo dõi chỉ số sinh hiệu và hẹn tái khám trong vòng hai tuần tới.",
        ),
        (
            "Cảnh báo: Cần theo dõi sát. Triệu chứng hiện tại chưa nguy cấp nhưng vẫn cần đánh giá thêm để phòng biến chứng tim mạch.",
            "Cảnh báo: Cần theo dõi sát. Triệu chứng hiện tại chưa nguy cấp nhưng vẫn cần đánh giá thêm để phòng biến chứng tim mạch.",
        ),
    ],
)
def test_add_paragraph_breaks_normalizes_vietnamese_section_separator(raw, expected):
    assert doctor_graph._add_paragraph_breaks(raw) == expected


def test_add_paragraph_breaks_formats_dense_numbered_and_star_lists():
    raw = (
        "Phân tích- Đái tháo đường type 2: Đường huyết lúc đói 7.2 mmol/L. "
        "Đề xuất: Dựa trên thông tin hiện có, có thể đề xuất các điều chỉnh sau:1. "
        "**Đái tháo đường type 2:***Tiếp tục Metformin: Thuốc này là nền tảng điều trị. "
        "*Cân nhắc tăng liều Metformin: Có thể tăng liều nếu dung nạp tốt. "
        "2. **Tăng huyết áp:***Tiếp tục Amlodipine: Thuốc này là lựa chọn tốt. "
        "*Thêm thuốc hạ huyết áp khác: Cân nhắc ACEi hoặc ARB nếu cần."
    )

    formatted = doctor_graph._add_paragraph_breaks(raw)

    assert "Phân tích : Đái tháo đường type 2" in formatted
    assert "các điều chỉnh sau:\n\n1. **Đái tháo đường type 2:**" in formatted
    assert "\n- Tiếp tục Metformin:" in formatted
    assert "\n- Cân nhắc tăng liều Metformin:" in formatted
    assert "\n\n2. **Tăng huyết áp:**" in formatted
    assert "\n- Tiếp tục Amlodipine:" in formatted
    assert "\n- Thêm thuốc hạ huyết áp khác:" in formatted


@pytest.mark.asyncio
async def test_resolve_patients_requires_single_selection_for_ambiguous_single_name(monkeypatch):
    patients = [
        {"id": "p1", "full_name": "Nguyễn Thị Lan", "primary_diagnosis": "I10"},
        {"id": "p2", "full_name": "Phạm Mai Lan", "primary_diagnosis": "E11"},
    ]
    monkeypatch.setattr(doctor_graph, "get_supabase", lambda: _FakeSupabase(patients))

    requests = []
    user_responses = iter(
        [
            {"patient_ids": ["p1", "p2"]},  # invalid for single-selection policy
            {"patient_ids": ["p2"]},        # valid
        ]
    )

    def _mock_interrupt(request):
        requests.append(request)
        return next(user_responses)

    monkeypatch.setattr(doctor_graph, "interrupt", _mock_interrupt)

    state = {
        "mentioned_patient_names": ["Lan"],
        "query_en": "Cho toi biet tinh trang cua benh nhan Lan",
        "enable_hitl": False,
        "enable_patient_confirmation_hitl": True,
    }

    result = doctor_graph.resolve_patients_node(state)

    assert len(requests) == 2
    assert requests[0]["type"] == "patient_confirmation"
    assert requests[0]["details"]["require_single_selection"] is True
    assert requests[0]["details"]["selection_reason"]
    assert requests[1]["details"]["validation_error"] == "Vui lòng chọn chính xác 1 bệnh nhân để tiếp tục."

    assert len(result["matched_patients"]) == 1
    assert result["matched_patients"][0]["id"] == "p2"
