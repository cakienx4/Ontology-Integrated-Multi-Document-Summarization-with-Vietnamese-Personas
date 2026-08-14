from pipeline.civilian.community import determine_community, INTENSITY_HIGH_THRESHOLD
from pipeline.civilian.worlds import build_worlds
from pipeline.civilian.ontology_context import build_ontology_context, load_graph
from pipeline.civilian.content_classifier import classify_content

TYPE_INSTRUCTIONS = {
    "Tin tức": "Giữ đúng trình tự thời gian và các yếu tố chính (ai, gì, khi nào, ở đâu, vì sao) của sự kiện.",
    "Bài chuyên sâu / Phân tích": "BẮT BUỘC giữ lại mạch lập luận chính và các luận điểm/phản biện quan trọng — không được chỉ liệt kê sự kiện bề mặt mà bỏ qua lập luận.",
    "Blog / Tản văn": "Giữ giọng văn và cảm xúc chủ đạo của tác giả, không chuyển sang giọng văn khách quan trung lập.",
    "Hướng dẫn / How-to": "BẮT BUỘC giữ đúng thứ tự các bước thực hiện, không đảo lộn, gộp tắt hay bỏ sót bước nào — kể cả khi bước đó ít liên quan đến persona. Bỏ bước sẽ khiến hướng dẫn không thể thực hiện được.",
    "Phỏng vấn": "Giữ lại các câu trả lời/quan điểm chính của người được phỏng vấn, có thể lược câu hỏi nếu không cần thiết.",
    "Thông báo / Thông cáo": "BẮT BUỘC giữ nguyên các thông tin hành chính cốt lõi (ngày hiệu lực, đối tượng áp dụng, thời hạn) dù không liên quan trực tiếp đến persona — đây là thông tin bắt buộc, không được lược bỏ vì lý do cá nhân hóa.",
    "Phóng sự / Ký sự": "Giữ lại các chi tiết mô tả hiện trường/bối cảnh quan trọng để duy trì tính chân thực của phóng sự.",
    "Đánh giá / Review": "Giữ lại kết luận đánh giá và các ưu/nhược điểm cốt lõi được đề cập.",
}

FOREIGN_POLICY_SIGNALS = [
    "liên minh châu âu", "châu âu", " eu ", "eu,", "eu.", "gdpr", "cbam",
    "đạo luật ai", "ai act", "hoa kỳ", "bang california", "california",
    "quy định của eu", "quy định của mỹ", "luật liên bang", "đạo luật liên bang",
    "chính sách nước ngoài", "quy định nước ngoài", "xuất khẩu sang", "thuế quan",
]


def _mentions_foreign_policy(text: str) -> bool:
    t = text.lower()
    return any(sig in t for sig in FOREIGN_POLICY_SIGNALS)


def build_neutral_prompt(text: str) -> str:
    n_words = len(text.split())
    max_words = int(n_words * 0.7)
    return f"""Bạn là hệ thống tóm tắt văn bản khách quan.

Hãy tóm tắt văn bản dưới đây một cách trung lập, đầy đủ ý chính, không thiên vị theo bất kỳ góc nhìn cá nhân nào. Độ dài bản tóm tắt KHÔNG ĐƯỢC VƯỢT QUÁ {max_words} từ (bản gốc có {n_words} từ). Không thêm thông tin ngoài văn bản gốc.

VĂN BẢN GỐC CẦN TÓM TẮT
{text}

Hãy viết bản tóm tắt khách quan. Chỉ trả về bản tóm tắt, không giải thích thêm.
"""


def build_prompt(row: dict, text: str, g, content_meta: dict = None) -> str:
    community = determine_community(row)
    worlds = build_worlds(row)
    ontology_context = build_ontology_context(g)

    n_words = len(text.split())
    max_words = int(n_words * 0.7)

    xac_nhan = worlds["xac_nhan"]
    gia_tuong = worlds["gia_tuong"]

    lang_level = community["Language"]["level"]
    lang_desc = community["Language"]["description"]

    lang_instruction_map = {
        1: "Dùng ngôn ngữ đơn giản, câu ngắn, từ ngữ đời thường. Tuyệt đối không dùng thuật ngữ chuyên môn.",
        2: "Dùng ngôn ngữ rõ ràng, dễ hiểu. Hạn chế thuật ngữ chuyên môn, nếu có thì giải thích ngắn gọn.",
        3: "Có thể dùng thuật ngữ phổ thông. Lập luận rõ ràng, cụ thể.",
        4: "Có thể dùng thuật ngữ chuyên môn. Lập luận nhiều tầng, giữ lại số liệu và chi tiết kỹ thuật.",
    }
    lang_instruction = lang_instruction_map[lang_level]

    topic_str = ", ".join(community["Topic"]["hard"][:3])
    soft_topics = community["Topic"]["soft"]

    domain_str = ", ".join(community["Domain"])
    cultural_str = community["Cultural"]["context"]
    prototype_str = community["Prototype"]
    sex_str = row.get("sex", "")

    region_str = row.get("region", "")
    zone_str = row.get("zone", "")
    orientation_str = community["Cultural"]["orientation"]

    country_str = row.get("country", "Việt Nam")

    if _mentions_foreign_policy(text):
        rule10 = (
            f"10. Người dùng có quốc gia: {country_str}. Văn bản gốc có đề cập chính sách/luật pháp/quy định "
            f"của quốc gia hoặc khu vực KHÁC với {country_str}. PHẢI chú thích rõ ràng trong bản tóm tắt rằng "
            f"các quy định đó KHÔNG áp dụng trực tiếp cho người đọc tại {country_str} — chỉ mang tính tham khảo "
            f"hoặc ảnh hưởng gián tiếp (ví dụ qua xuất khẩu, hợp tác quốc tế). Không được trình bày như thể các "
            f"quy định này có hiệu lực pháp lý trực tiếp trong nước."
        )
    else:
        rule10 = ""

    region_instruction = (
        f"Nếu văn bản đề cập nhiều vùng miền khác nhau, đây là dạng phân nhánh theo Rule 1b: "
        f"nội dung liên quan đến {region_str} (vùng {zone_str}) PHẢI được giữ đầy đủ, chi tiết; "
        f"các vùng miền khác chỉ nêu ngắn gọn 1 câu, không đi vào số liệu/chi tiết cụ thể."
    )

    cultural_instruction = (
        f"Góc độ văn hóa của người dùng là '{orientation_str}'. Nếu văn bản đề cập song song nhiều "
        f"xu hướng văn hóa (ví dụ: truyền thống vs hiện đại), đây là dạng phân nhánh theo Rule 1b: "
        f"nhánh khớp với '{orientation_str}' PHẢI giữ đầy đủ, chi tiết; nhánh còn lại chỉ nêu ngắn gọn "
        f"1 câu, không đi vào chi tiết cụ thể."
    )

    # thêm sau đoạn cultural_instruction trong build_prompt()
    family_context_str = xac_nhan["family_context"]
    marital_instruction = (
        f"Tình trạng hôn nhân/gia đình của người dùng: {family_context_str}. Nếu văn bản đề cập song song "
        f"nội dung phù hợp gia đình/trẻ nhỏ VÀ nội dung phù hợp cá nhân/độc lập (ví dụ: điểm đến gia đình vs. "
        f"trải nghiệm cá nhân), đây là dạng phân nhánh theo Rule 1b: nhánh khớp với tình trạng hôn nhân trên "
        f"PHẢI giữ đầy đủ, chi tiết; nhánh còn lại chỉ nêu ngắn gọn 1 câu, không đi vào chi tiết cụ thể."
    )

    if content_meta is None:
        content_meta = classify_content(text)
    print(f"[DEBUG] type={content_meta['type']} | genre={content_meta['genre']} | text[:30]={text[:30]}")

    text_type = content_meta["type"]
    text_genre = content_meta["genre"]
    type_instruction = TYPE_INSTRUCTIONS.get(text_type, "")

    # Dùng để khớp với soft_topics (sở thích cá nhân) — PHẢI dùng tên nhãn ngắn, khớp key trong community.py
    GENRE_TO_INTEREST_LABEL = {
        "Du lịch": "Du lịch",
        "Nấu ăn / Ẩm thực": "Ẩm thực",
        "Thể thao": "Thể thao",
        "Giải trí / Văn hóa": "Nghệ thuật",
    }

    # Dùng để khớp với community["Domain"] (chuyên môn/expertise) — giữ nguyên như đã fix cho CQ8/CQ11
    GENRE_TO_DOMAIN_LABELS = {
        "Tài chính / Kế toán": {"Tài chính / Kế toán", "Quản lý / Tổ chức"},
        "Công nghệ / Kỹ thuật số": {"Công nghệ / Kỹ thuật số", "Sáng tạo / Nghệ thuật"},
        "Giải trí / Văn hóa": {"Sáng tạo / Nghệ thuật"},
        "Du lịch": {"Du lịch / Lữ hành"},
        "Nấu ăn / Ẩm thực": {"Nấu ăn / Ẩm thực"},
        "Y tế / Chăm sóc": {"Y tế / Chăm sóc"},
        "Thể thao": {"Thể thao"},
        "Giáo dục": {"Giáo dục / Học thuật"},
        "Chính trị / Pháp luật": {"Pháp lý / Pháp luật"},
        "Môi trường": {"Nông nghiệp / Tự nhiên"},
        "Thời sự / Xã hội": set(),
    }

    relevant_label = GENRE_TO_INTEREST_LABEL.get(text_genre)
    entry = soft_topics.get(relevant_label) if relevant_label else None

    if entry and entry["intensity"] >= INTENSITY_HIGH_THRESHOLD:
        interests_block = (
            f"Sở thích cá nhân liên quan trực tiếp đến chủ đề văn bản — {relevant_label}: "
            f"{entry['summary']} (SOFT — chỉ ưu tiên khi KHÔNG mâu thuẫn với đặc trưng cứng, theo Rule 6). "
            f"HÃY DÙNG văn phong giàu hình ảnh, ẩn dụ, gợi cảm xúc khi mô tả nội dung liên quan đến "
            f"'{relevant_label}'. LƯU Ý: chỉ dẫn này chỉ thay đổi CÁCH DIỄN ĐẠT câu chữ, KHÔNG được dùng để "
            f"thay thế hoặc lược bỏ nội dung phân tích chuyên môn/kỹ thuật (nếu người dùng có domain chuyên môn "
            f"trùng với lĩnh vực văn bản, xem 'Lĩnh vực văn bản' bên dưới) — 2 yêu cầu này phải cùng tồn tại "
            f"trong bản tóm tắt, không đánh đổi cái này lấy cái kia."
        )
    else:
        interests_block = (
            f"Người dùng không có sở thích/kinh nghiệm rõ rệt với lĩnh vực '{text_genre}'. "
            f"Dùng văn phong trực tiếp, tường minh, không cần ngôn ngữ giàu hình ảnh/ẩn dụ — kể cả khi đoạn "
            f"văn bản gốc giữ lại (do khớp Rule 1b) vốn giàu hình ảnh; PHẢI viết lại theo văn phong trực tiếp."
        )

    travel_branch_instruction = ""
    if relevant_label == "Du lịch" and entry and entry["subtopic"]:
        travel_branch_instruction = (
            f"Phong cách du lịch của người dùng nghiêng về '{entry['subtopic']}' (dựa trên travel_persona: "
            f"{entry['summary']}). Nếu văn bản có nhiều nhánh nội dung du lịch khác nhau, đây là phân nhánh "
            f"theo Rule 1b: nhánh khớp '{entry['subtopic']}' PHẢI giữ đầy đủ, chi tiết; nhánh còn lại chỉ nêu "
            f"ngắn gọn 1 câu."
        )

    user_domains = set(community["Domain"])
    overlap_domains = GENRE_TO_DOMAIN_LABELS.get(text_genre, set())
    domain_overlap = bool(user_domains & overlap_domains)

    if domain_overlap:
        genre_depth_note = (
            f"Văn bản thuộc lĩnh vực '{text_genre}', trùng với chuyên môn người dùng đã có "
            f"({', '.join(user_domains)}) — không cần giải thích khái niệm nền tảng của lĩnh vực này. "
            f"BẮT BUỘC giữ lại các thuật ngữ/chi tiết kỹ thuật chuyên môn xuất hiện trong văn bản gốc "
            f"(ví dụ: kỹ thuật, phong cách, trường phái, phối màu, bố cục, chất liệu...) — không được thay "
            f"bằng mô tả cảm xúc/hình ảnh chung chung, kể cả khi mục 'Chủ đề hứng thú' yêu cầu văn phong giàu hình ảnh."
        )
    else:
        genre_depth_note = (
            f"Văn bản thuộc lĩnh vực '{text_genre}', KHÔNG trùng với chuyên môn hiện có của "
            f"người dùng — cần giữ lại phần giải thích nền tảng cần thiết, không giả định "
            f"người đọc đã quen thuộc với lĩnh vực này."
        )

    is_structural_type = text_type in ("Hướng dẫn / How-to", "Thông báo / Thông cáo")
    if is_structural_type:
        rule9 = (
            f"9. Đây là văn bản có cấu trúc bắt buộc — {type_instruction} "
            f"Quy tắc này có độ ưu tiên CAO HƠN Rule 1, 2, 6 khi xảy ra xung đột: "
            f"không được lược bỏ phần cấu trúc bắt buộc dù nó không phù hợp persona."
        )
    else:
        rule9 = ""

    prompt = f"""Bạn là hệ thống tóm tắt văn bản cá nhân hóa. Nhiệm vụ CHÍNH của bạn KHÔNG PHẢI là tóm tắt khách quan văn bản, mà là chọn lọc và nhấn mạnh lại nội dung văn bản DƯỚI GÓC NHÌN của đúng người dùng được mô tả dưới đây — giống như một biên tập viên viết lại bản tin cho một độc giả cụ thể, không phải một máy tóm tắt trung lập.

    PHẦN 1: KHUNG PHÂN TÍCH PERSONA (Ontology Context)
    Đây là cấu trúc các đặc điểm persona và mối quan hệ giữa chúng. Dùng để hiểu cách các yếu tố của người dùng liên kết với nhau:
    {ontology_context}

    PHẦN 2: HỒ SƠ NGƯỜI DÙNG

    [Hình mẫu đại diện]
    {prototype_str}
    [Giới tính người dùng]
    {sex_str}

    [Thế giới xác nhận — thông tin chính xác, bắt buộc phản ánh đúng]
    {xac_nhan["statement"]}

    [Thế giới giả tưởng — động lực và định hướng nội tâm]
    - Bổn phận: {gia_tuong["Bổn phận"]}
    - Mong muốn: {gia_tuong["Mong muốn"]}
    - Niềm tin: {gia_tuong["Niềm tin"]}


    PHẦN 3: CHỈ DẪN TÓM TẮT

    Văn phong: {lang_instruction} (Đặc điểm người nhận: {lang_desc})
    Chủ đề ưu tiên giữ lại: {topic_str}
    Lĩnh vực người dùng đã am hiểu (không cần giải thích cơ bản): {domain_str}
    Góc độ vùng miền: {region_instruction}
    Góc độ văn hóa: {cultural_str} — {cultural_instruction}
    Kiểu bài viết: {text_type} — {type_instruction}
    Lĩnh vực văn bản: {text_genre} — {genre_depth_note}
    Chủ đề hứng thú: {interests_block}
    Góc độ hôn nhân/gia đình: {marital_instruction}
    Phong cách du lịch (nếu có nhánh nội dung khác nhau): {travel_branch_instruction if travel_branch_instruction else "Không áp dụng."}

    QUAN TRỌNG — kiểm tra trước khi viết: nếu hai người dùng khác nhau đọc cùng một văn bản gốc, hai bản tóm tắt của bạn PHẢI khác nhau rõ rệt về nội dung được giữ lại/nhấn mạnh, không chỉ khác nhau về cách diễn đạt câu chữ. Nếu bạn thấy bản tóm tắt mình sắp viết gần như có thể dùng chung cho bất kỳ ai, đó là dấu hiệu bạn đang tóm tắt trung lập thay vì lọc theo persona — hãy viết lại.

    Nguyên tắc bắt buộc:
    1. CHỦ ĐỘNG loại bỏ — không chỉ "ưu tiên giữ lại" — những đoạn/ý trong văn bản gốc không phù hợp với hồ sơ người dùng trên. Không liệt kê đầy đủ mọi ý của văn bản gốc rồi để nguyên; phải thực sự cắt bỏ phần không liên quan.
    1b. Nếu văn bản gốc chứa nhiều chủ đề/nhánh nội dung khác nhau (ví dụ: nhiều lĩnh vực, nhiều đối tượng độc giả, hoặc nội dung phân chia theo đặc điểm như giới tính/độ tuổi/nghề nghiệp/NHIỀU VÙNG MIỀN khác nhau/CÁC XU HƯỚNG VĂN HÓA đối lập như truyền thống-hiện đại/CÁC PHONG CÁCH-SỞ THÍCH KHÁC NHAU như thiên nhiên-sinh thái vs lịch sử-văn hóa, khám phá vs nghỉ dưỡng), hãy xác định nhánh nào phù hợp nhất với hồ sơ người dùng (dựa trên Domain, Topic, Hình mẫu đại diện, VÀ chỉ dẫn cụ thể ở mục 'Chủ đề hứng thú' / 'Phong cách du lịch' ở trên nếu có — các chỉ dẫn SOFT này có độ ưu tiên ngang với Domain/Topic khi quyết định nhánh nào được giữ). Nhánh phù hợp nhất: tóm tắt bình thường theo Rule 1-3, đủ ý, không bị nén quá mức. Các nhánh còn lại: KHÔNG loại bỏ hoàn toàn — nêu trong 1 cụm từ/câu ngắn gọn (không chi tiết, không số liệu), độ dài phải NGẮN HƠN RÕ RỆT so với nhánh phù hợp nhất. Nội dung áp dụng chung cho mọi nhánh (không phân biệt) vẫn tóm tắt bình thường như các ý liên quan khác.
    2. Chỉ giữ lại thông tin phù hợp với hồ sơ người dùng trên.
    3. Không thêm thông tin ngoài văn bản gốc. Không diễn giải, không phân tích hệ quả, không thêm lời khuyên. Persona chỉ là "màng lọc" để quyết định giữ lại gì, không phải để sáng tác thêm.
    4. Không giải thích lại những gì người dùng đã thành thạo trong lĩnh vực: {domain_str}.
    5. Phản ánh đúng thế giới xác nhận — không suy diễn thêm về người dùng.
    6. Ưu tiên nội dung theo thứ bậc: đặc trưng cứng (tuổi, trình độ học vấn, nghề nghiệp, khu vực sống) có trọng số cao hơn đặc trưng mềm (sở thích du lịch, nghệ thuật, thể thao). Khi hai nhóm gợi ý nội dung MÂU THUẪN nhau, chỉ giữ lại nội dung phù hợp với đặc trưng cứng và LƯỢC BỎ HẲN nội dung chỉ phù hợp với đặc trưng mềm — không được liệt kê cả hai bên rồi để người đọc tự chọn, không được nhắc đến phương án mâu thuẫn với đặc trưng cứng dù chỉ để đối chiếu. LƯU Ý: Rule này CHỈ áp dụng cho việc chọn NỘI DUNG được giữ lại/lược bỏ, KHÔNG áp dụng cho VĂN PHONG/GIỌNG ĐIỆU — văn phong luôn tuân theo đúng chỉ dẫn ở mục 'Chủ đề hứng thú', kể cả khi nghề nghiệp của người dùng gợi ý một giọng điệu khác.
    7. Độ dài bản tóm tắt KHÔNG ĐƯỢC VƯỢT QUÁ {max_words} từ (bản gốc có {n_words} từ). Nếu văn bản gốc quá ngắn để tóm tắt đủ, hãy viết tóm tắt ngắn hơn gốc theo đúng độ dài trên, kể cả khi chỉ còn 1 câu. Chỉ giữ lại các ý chính liên quan đến persona, lược bỏ phần còn lại. Không được thêm câu hoặc ý không có trong văn bản gốc dù với bất kỳ lý do nào.
    8. BẮT BUỘC luôn phải trả về một bản tóm tắt bằng văn bản đầy đủ, có nghĩa, dù mức độ liên quan giữa văn bản gốc và hồ sơ người dùng thấp đến đâu. Tuyệt đối không được: để trống, chỉ trả về dấu câu/ký tự placeholder (như "-", "...", "N/A"), hoặc viết các câu như "không có nội dung phù hợp". Đây là trường hợp DUY NHẤT được phép tóm tắt trung lập — chỉ khi văn bản gốc THỰC SỰ không có bất kỳ nội dung nào liên quan đến bất kỳ trường persona nào (kể cả HARD lẫn SOFT). Khi đó, tóm tắt ý chính, thực chất nhất của văn bản gốc (vẫn giữ yêu cầu ngắn gọn ở Rule 7), áp dụng văn phong đã chỉ định ở trên. Ngược lại, nếu văn bản có bất kỳ nội dung nào liên quan đến persona, bắt buộc phải áp dụng đầy đủ Rule 1, 2, 6 ở trên — không được lấy Rule 8 làm lý do để tóm tắt khách quan/đầy đủ mọi phía.
    9. {rule9}
    10. {rule10}

    PHẦN 4: VĂN BẢN GỐC CẦN TÓM TẮT

    {text}
    Hãy viết bản tóm tắt cá nhân hóa cho người dùng trên. Chỉ trả về bản tóm tắt, không giải thích thêm.
    """
    return prompt


def build_brief_prompt(text: str) -> str:
    return f"""Đọc văn bản dưới đây và viết đúng 1-2 câu nêu chủ đề chính, không đi vào chi tiết,
không số liệu cụ thể. Đây chỉ là phần nhắc qua, không phải tóm tắt đầy đủ.

VĂN BẢN:
{text}

Chỉ trả về 1-2 câu, không giải thích thêm.
"""


if __name__ == "__main__":
    import pandas as pd

    g = load_graph("../ontology/persona_analysis_3.ttl")
    df = pd.read_csv("../../data/sample50.csv")

    sample_text = """Lễ hội pháo hoa quốc tế Đà Nẵng năm nay dự kiến diễn ra từ ngày 31/5 đến 12/7,
với sự tham gia của 8 đội đến từ các quốc gia như Ý, Úc, Mỹ, Phần Lan và Việt Nam.
Ban tổ chức cho biết lễ hội năm nay sẽ có thêm khu vực trải nghiệm ẩm thực đường phố
kết hợp với các gian hàng thủ công mỹ nghệ truyền thống. Vé xem pháo hoa dao động từ
200.000 đến 800.000 đồng tùy vị trí khán đài. Ngoài ra, du khách đến từ các tỉnh thành
khác có thể đặt tour trọn gói bao gồm vé máy bay, khách sạn và vé xem pháo hoa thông
qua các đại lý du lịch. Ban tổ chức khuyến cáo người xem nên đến sớm ít nhất 1 tiếng
để tìm chỗ đỗ xe và ổn định chỗ ngồi, đồng thời chuẩn bị áo mưa vì thời tiết tháng 6
tại Đà Nẵng thường có mưa bất chợt."""

    row = df.iloc[2].to_dict()
    prompt = build_prompt(row, sample_text, g)
    print(prompt)
    print(f"\n--- Tổng độ dài prompt: {len(prompt)} ký tự ---")
