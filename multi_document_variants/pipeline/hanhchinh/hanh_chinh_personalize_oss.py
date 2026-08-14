import json
import re
import asyncio
from pathlib import Path

from pipeline.utils import retry_generate_async, OSS_MODEL_NAME, load_graph, tao_oss_client_async, OSS_MAX_CONCURRENCY
from pipeline.profiles.ontology_context_state import lay_ontology_context_cho_nganh

ROOT_DIR = Path(__file__).resolve().parents[2]
_ONTOLOGY_PATH = ROOT_DIR / "persona_states.ttl"
_STATE_GRAPH = load_graph(str(_ONTOLOGY_PATH))

# ==== BƯỚC 1: XÁC ĐỊNH TẦNG ĐỘ SÂU CHO TỪNG MỤC + STYLE TOÀN BÀI ====

TANG_CHUYEN_SAU = 0
TANG_TRUNG_BINH = 1
TANG_NEN = 2


def _chi_so_da_khop_persona(persona_id, ket_qua_khop_persona):
    ket_qua = {}
    for entry in ket_qua_khop_persona:
        if persona_id not in entry.get("danh_sach_persona_id_khop", []):
            continue

        chi_so_goc = entry.get("chi_so_doi_tuong_goc")
        if chi_so_goc is None:
            continue

        do_tin_cay = entry.get("do_tin_cay", "thap")

        if do_tin_cay == "trung bình" and persona_id in entry.get(
                "danh_sach_persona_id_khop_ca_nganh_nho", []
        ):
            do_tin_cay = "cao"

        ket_qua[chi_so_goc] = do_tin_cay
    return ket_qua


def gan_tang_do_sau_va_style(persona_id, danh_sach_muc, ket_qua_khop_persona):
    chi_so_theo_do_tin_cay = _chi_so_da_khop_persona(persona_id, ket_qua_khop_persona)

    co_cao = "cao" in chi_so_theo_do_tin_cay.values()
    co_trung_binh = "trung bình" in chi_so_theo_do_tin_cay.values()

    if co_cao:
        style = "chuyen_sau"
    elif co_trung_binh:
        style = "khong_chuyen_mon"
    else:
        style = "binh_thuong"

    danh_sach_muc_moi = []
    for muc in danh_sach_muc:
        chi_so_lien_quan = muc.get("chi_so_doi_tuong_lien_quan", [])
        do_tin_cay_cua_muc = [
            chi_so_theo_do_tin_cay[cs] for cs in chi_so_lien_quan
            if cs in chi_so_theo_do_tin_cay
        ]

        if "cao" in do_tin_cay_cua_muc:
            tang = TANG_CHUYEN_SAU
        elif "trung bình" in do_tin_cay_cua_muc:
            tang = TANG_TRUNG_BINH
        else:
            tang = TANG_NEN

        muc_moi = dict(muc)
        muc_moi["tang_do_sau"] = tang
        danh_sach_muc_moi.append(muc_moi)

    return danh_sach_muc_moi, style


# ==== BƯỚC 2: TEXT HƯỚNG DẪN THEO TẦNG ĐỘ SÂU VÀ THEO STYLE ====

MUC_DO_THEO_TANG = {
    TANG_CHUYEN_SAU: (
        "Đây là phần LIÊN QUAN TRỰC TIẾP nhất tới công việc/chuyên môn của "
        "người đọc (khớp đúng, cụ thể). Tóm tắt ĐẦY ĐỦ, không bỏ sót nội dung "
        "quan trọng. Giữ nguyên nhiệm vụ cụ thể, tên cơ quan/đơn vị, số liệu "
        "thực tế và mốc thời gian thực tế có trong nội dung gốc. Người đọc CÓ "
        "chuyên môn đúng lĩnh vực này nên sử dụng thuật ngữ hành chính, pháp lý "
        "hoặc chuyên ngành một cách tự nhiên, KHÔNG cần giải thích lại các khái "
        "niệm cơ bản."

        " Khi giữ số liệu, CHỈ giữ các số liệu phản ánh nội dung thực tế của văn "
        "bản như tỷ lệ, số lượng, chỉ tiêu, mục tiêu, kinh phí, thời hạn, lộ "
        "trình, ngày tháng thực hiện và các số liệu thống kê phục vụ nội dung."

        " TUYỆT ĐỐI KHÔNG coi số hiệu, ký hiệu hoặc ngày ban hành của các văn bản "
        "viện dẫn là số liệu cần giữ. Không đưa vào bản tóm tắt các chuỗi như "
        "'777/TTg-TCCV', '1186/KH-BGDĐT', '4054/BGDĐT-GDPT'... Nếu cần nhắc tới "
        "văn bản thì chỉ ghi loại văn bản (Quyết định, Kế hoạch, Công văn...) "
        "mà không ghi số hiệu."
    ),
    TANG_TRUNG_BINH: (
        "Đây là phần liên quan ở mức CHUNG, không phải chuyên môn trực tiếp của "
        "người đọc. Bản tóm tắt vẫn phải BAO QUÁT đầy đủ các nội dung chính của "
        "mục, chỉ lược bỏ các chi tiết quá nhỏ hoặc mang tính kỹ thuật. Giữ các "
        "nhiệm vụ chính, phương án thực hiện, số liệu thực tế, mốc thời gian và "
        "đơn vị quan trọng. Người đọc KHÔNG CÓ chuyên môn đúng lĩnh vực này nên "
        "dùng ngôn ngữ phổ thông, dễ hiểu; đối với các thuật ngữ hành chính hoặc "
        "pháp lý thì PHẢI giải thích ngắn gọn ngay trong câu."
    ),
}

TANG_NEN_THEO_STYLE = {
    "chuyen_sau": (
        "Đây là phần NỀN, không thuộc đúng chuyên môn của người đọc nhưng vẫn là "
        "một phần của văn bản cần nắm được. Bản tóm tắt phải BAO QUÁT đầy đủ nội "
        "dung chính của mục này, không chỉ nêu đại ý. Giữ các nhiệm vụ chính, số "
        "liệu thực tế, mốc thời gian và tên đơn vị quan trọng; chỉ lược bỏ các "
        "chi tiết quá nhỏ hoặc lặp lại. Dùng ngôn ngữ hành chính tự nhiên nhưng "
        "không đi sâu phân tích như tầng chuyên sâu."
    ),
    "khong_chuyen_mon": (
        "Đây là phần NỀN, không thuộc đúng chuyên môn của người đọc. Bản tóm tắt "
        "phải bao quát đầy đủ nội dung chính của mục, giữ các nhiệm vụ chính, số "
        "liệu thực tế, mốc thời gian và đơn vị quan trọng. Dùng ngôn ngữ phổ "
        "thông, dễ hiểu; đối với thuật ngữ hành chính hoặc pháp lý thì PHẢI giải "
        "thích ngắn gọn ngay trong câu."
    ),
    "binh_thuong": (
        "Đây là phần NỀN, không liên quan trực tiếp tới công việc của người đọc "
        "nhưng vẫn cần được tóm tắt để người đọc hiểu bức tranh chung của văn "
        "bản. Bản tóm tắt phải BAO QUÁT các nội dung chính của mục này, phản ánh "
        "được mục tiêu, yêu cầu, nhiệm vụ hoặc phương án quan trọng nếu có. Chỉ "
        "lược bỏ các chi tiết quá nhỏ, danh sách dài hoặc thông tin mang tính kỹ "
        "thuật. Ưu tiên diễn đạt bằng ngôn ngữ phổ thông, đơn giản, dễ hiểu. "
        "Không bắt buộc giữ mọi số liệu, nhưng phải giữ các số liệu và mốc thời "
        "gian thực tế có ý nghĩa đối với nội dung; không giữ số hiệu, ký hiệu "
        "hoặc ngày ban hành của các văn bản viện dẫn."
    ),
}

# Quy tắc GỘP MỤC NỀN chỉ áp dụng cho style "binh_thuong" (toàn bộ văn bản
# không liên quan gì tới người đọc). Với "chuyen_sau" và "khong_chuyen_mon",
# KHÔNG gộp nữa - mỗi mục nền vẫn có đoạn riêng, tóm tắt đầy đủ ý hơn (nhưng
# vẫn tuân đúng yêu cầu tầng nền: không liệt kê số liệu/mốc thời gian/tên đơn
# vị cụ thể, không dùng thuật ngữ chuyên ngành khác lĩnh vực).
GOP_MUC_NEN_THEO_STYLE = {
    "chuyen_sau": (
        "- KHÔNG gộp các mục tầng nền lại với nhau. Mỗi mục (kể cả mục tầng "
        "nền) vẫn có đoạn/câu riêng theo đúng \"Yêu cầu cho mục này\" đã ghi ở "
        "trên - tức là VẪN GIỮ số liệu/mốc thời gian/tên đơn vị cụ thể của "
        "mục đó, không tóm chung chung, không cắt bỏ chi tiết."
    ),
    "khong_chuyen_mon": (
        "- KHÔNG gộp các mục tầng nền lại với nhau. Mỗi mục (kể cả mục tầng "
        "nền) vẫn có đoạn/câu riêng theo đúng \"Yêu cầu cho mục này\" đã ghi ở "
        "trên - tức là VẪN GIỮ số liệu/mốc thời gian/tên đơn vị cụ thể của "
        "mục đó, không tóm chung chung, không cắt bỏ chi tiết."
    ),
    "binh_thuong": (
        "- Không bắt buộc viết một đoạn văn tách biệt cho MỌI mục: nếu nhiều mục "
        "liên tiếp cùng thuộc tầng \"nền\" và có nội dung gần nhau, CÓ THỂ gộp "
        "chung thành một đoạn cho mạch văn tự nhiên, không tách rời cứng nhắc. "
        "TUY NHIÊN việc gộp KHÔNG được đánh đổi lấy việc bỏ sót nội dung: đoạn "
        "gộp đó vẫn PHẢI phản ánh đầy đủ các nhóm nội dung chính của TẤT CẢ các "
        "mục được gộp (mục tiêu, yêu cầu, nhiệm vụ, phương án... nếu có), theo "
        "đúng thứ tự so với văn bản gốc - không được gộp rồi chỉ giữ 1 câu đại "
        "ý chung chung làm mất nội dung của các mục khác trong cụm. Không có "
        "yêu cầu phải viết ngắn - độ dài do nội dung cần bao quát quyết định."
    ),
}


# ==== BƯỚC 3: DỰNG PROMPT ====

def _dinh_dang_danh_sach_muc(danh_sach_muc, style):
    ds = ""
    yeu_cau_tang_nen = TANG_NEN_THEO_STYLE.get(style, TANG_NEN_THEO_STYLE["binh_thuong"])
    for i, muc in enumerate(danh_sach_muc, 1):
        if muc.get("heading") is None and not muc.get("doan_van"):
            continue
        noi_dung = "\n   ".join(muc.get("doan_van", []))
        tang = muc.get("tang_do_sau", TANG_NEN)
        yeu_cau = MUC_DO_THEO_TANG[tang] if tang != TANG_NEN else yeu_cau_tang_nen
        ds += (
            f"\n{i}. Mục: \"{muc.get('heading') or '(không có tiêu đề riêng)'}\"\n"
            f"   Nội dung: {noi_dung}\n"
            f"   Yêu cầu cho mục này: {yeu_cau}\n"
        )
    return ds


def build_hanh_chinh_prompt(persona, ket_qua_extract, danh_sach_muc_voi_tang, style):
    loai_van_ban = ket_qua_extract.get("loai_van_ban", "")
    ontology_ctx = lay_ontology_context_cho_nganh(persona.get("nganh_to", ""))

    danh_sach_muc_text = _dinh_dang_danh_sach_muc(danh_sach_muc_voi_tang, style)
    quy_tac_gop_muc_nen = GOP_MUC_NEN_THEO_STYLE.get(
        style, GOP_MUC_NEN_THEO_STYLE["binh_thuong"]
    )

    ontology_section = ""
    if ontology_ctx:
        ontology_section = f"""
    PHẦN 1: KHUNG PHÂN TÍCH NGÀNH CÔNG VỤ (Ontology Context)
    {ontology_ctx}

    """

    prompt = f"""{ontology_section}Bạn đang tóm tắt cá nhân hóa 1 văn bản hành chính (loại: {loai_van_ban})
    cho một cán bộ có hồ sơ công vụ sau:

    - Ngành/lĩnh vực: {persona.get('nganh_to')} - {persona.get('nganh_nho')}
    - Đơn vị công tác: {persona.get('to_chuc')}
    - Mô tả chung: {persona.get('mo_ta_chung')}

    Dưới đây là toàn bộ nội dung văn bản, đã chia theo mục, GIỮ NGUYÊN THỨ TỰ như
    văn bản gốc. Mỗi mục có ghi rõ yêu cầu độ chi tiết VÀ văn phong riêng - PHẢI
    tuân thủ đúng yêu cầu đó cho TỪNG mục, không viết đều tay như nhau cho tất cả
    các mục kể cả về độ dài lẫn cách dùng từ ngữ:
    {danh_sach_muc_text}

    QUY TẮC BẮT BUỘC:
    - Viết thành bài tóm tắt liền mạch, TUYỆT ĐỐI giữ ĐÚNG THỨ TỰ các mục như văn
      bản gốc đã liệt kê ở trên - KHÔNG được đảo thứ tự, KHÔNG được đưa mục nào
      lên trước dù mục đó có tầng độ sâu cao hơn mục khác.
    - ĐỊNH DẠNG ĐẦU RA LÀ VĂN XUÔI THUẦN TÚY, KHÔNG CÓ NGOẠI LỆ, áp dụng cho MỌI
      văn bản bất kể số lượng mục nhiều hay ít, văn bản dài hay ngắn:
      + TUYỆT ĐỐI KHÔNG đánh số hoặc đặt tiêu đề cho mục dưới bất kỳ hình thức
        nào - kể cả "Mục 1:", "1.", "(1)", "Về mục thứ nhất:", in đậm tên mục,
        hay lặp lại nguyên văn heading gốc của mục làm câu mở đầu đoạn.
      + TUYỆT ĐỐI KHÔNG dùng gạch đầu dòng, danh sách liệt kê máy móc.
      + Sai (không được viết): "1. Về công tác an toàn thực phẩm: UBND yêu cầu..."
      + Đúng (phải viết): "Về công tác an toàn thực phẩm, UBND yêu cầu..." hoặc
        chuyển thẳng sang nội dung bằng câu dẫn tự nhiên, không tách dòng riêng
        cho từng mục.
      + Quy tắc này ĐÚNG NGUYÊN VẸN với mọi văn bản, không được nới lỏng chỉ vì
        văn bản có nhiều mục hoặc mục dài - càng nhiều mục càng phải viết liền
        mạch bằng câu dẫn chuyển ý, không phải bằng cách đánh số.
    - Với MỖI mục, tuân thủ ĐÚNG "Yêu cầu cho mục này" đã ghi kèm ở trên - lưu ý
      yêu cầu này đã khác nhau tùy theo tầng VÀ tùy theo hồ sơ người đọc, không
      áp một kiểu viết chung cho tất cả các mục.
    - BẮT BUỘC ÁP DỤNG QUY TẮC GỘP/KHÔNG GỘP MỤC TẦNG NỀN SAU ĐÂY, TUYỆT ĐỐI
      KHÔNG được làm khác:
    {quy_tac_gop_muc_nen}
    - KHÔNG tự suy luận, đánh giá hoặc thêm nhận định không có trong văn bản gốc.
    - KHÔNG chèn bất kỳ câu/cụm chú thích nào về quá trình viết bài (ví dụ:
      "(mục này được tóm gọn vì...)"). Bài trả về chỉ là văn bản tóm tắt tự nhiên.
    - Chỉ trả về nội dung văn bản, không thêm lời dẫn kiểu "Dưới đây là...".
    - QUY TẮC VỀ SỐ LIỆU:
      + CHỈ giữ các số liệu phản ánh nội dung thực tế của văn bản, bao gồm:
        * tỷ lệ, phần trăm;
        * số lượng cơ quan, đơn vị, trường học, cán bộ, người dân...;
        * chỉ tiêu, mục tiêu, kết quả;
        * kinh phí, diện tích, quy mô;
        * ngày, tháng, năm;
        * thời hạn, lộ trình, giai đoạn thực hiện;
        * các số liệu thống kê và thông tin định lượng phục vụ nội dung văn bản.
      + TUYỆT ĐỐI KHÔNG giữ hoặc nhấn mạnh số hiệu văn bản hành chính, bao gồm
        số quyết định, số công văn, số kế hoạch, số thông báo, số báo cáo, số
        nghị quyết, số chỉ thị hoặc bất kỳ chuỗi ký hiệu dạng
        "xxx/TTg-...", "xxx/QĐ-...", "xxx/KH-...", "xxx/CV-...",
        "xxx/UBND-...",...
      + Nếu câu chỉ khác nhau ở số hiệu văn bản thì bỏ số hiệu, giữ lại nội
        dung chính của câu.
      + Ví dụ:
          Sai: "Kế hoạch số 1186/KH-BGDĐT quy định..."
          Đúng: "Kế hoạch quy định..."
          Sai: "Quyết định số 777/TTg-TCCV yêu cầu..."
          Đúng: "Quyết định yêu cầu..."
          Đúng: "Thực hiện tinh gọn tối thiểu 50% đầu mối."
          Đúng: "Lộ trình sắp xếp 10 trường cao đẳng."
          Đúng: "Hoàn thành trước ngày 31/12/2026."
    - QUY TẮC GIẢI THÍCH THUẬT NGỮ (áp dụng cho đoạn thuộc tầng "trung bình",
      và tầng "nền" khi style tổng thể là "khong_chuyen_mon" hoặc "binh_thuong" -
      tức các đoạn dành cho người đọc KHÔNG có chuyên môn đúng lĩnh vực đó):
      + BẮT BUỘC mọi thuật ngữ hành chính, pháp lý hoặc chuyên ngành xuất hiện
        trong đoạn đó phải có phần giải thích ngắn gọn đi kèm NGAY TRONG CÙNG
        CÂU, không được để thuật ngữ đứng một mình không giải thích.
      + Cách giải thích: chèn cụm giải thích ngắn ngay sau thuật ngữ, có thể
        đặt trong dấu ngoặc đơn hoặc nối bằng dấu phẩy/cụm từ giải nghĩa tự
        nhiên - miễn là người không có chuyên môn đọc vẫn hiểu được nghĩa mà
        không cần tra cứu thêm.
      + Ví dụ:
          Sai: "Sở chủ trì xây dựng đề án sáp nhập các đơn vị sự nghiệp."
          Đúng: "Sở đứng ra tổ chức chính (chủ trì) xây dựng kế hoạch chi tiết
          (đề án) để gộp (sáp nhập) các đơn vị sự nghiệp lại với nhau."
          Sai: "UBND giao Sở Nội vụ thẩm định hồ sơ theo quy trình rút gọn."
          Đúng: "UBND giao Sở Nội vụ kiểm tra, xét duyệt (thẩm định) hồ sơ theo
          quy trình đơn giản, nhanh hơn bình thường (quy trình rút gọn)."
      + Quy tắc này KHÔNG áp dụng cho đoạn thuộc tầng "chuyên sâu", hoặc đoạn
        tầng "nền" khi style tổng thể là "chuyen_sau" - ở các đoạn đó thuật
        ngữ chuyên ngành được dùng tự nhiên, không cần giải thích lại.
      + LƯU Ý QUAN TRỌNG: "không có chuyên môn" ở đây là góc nhìn của NGƯỜI
        ĐỌC PHỔ THÔNG, không phải góc nhìn của người soạn văn bản hành chính.
        Rất nhiều từ NGHE có vẻ thông dụng trong văn bản nhà nước (ví dụ:
        "quy hoạch tổng thể", "xã hội hóa", "tinh giản biên chế", "dự án đầu
        tư công", "tài sản công", "đề án", "sáp nhập", "phân cấp", "thẩm
        định") VẪN PHẢI giải thích ở tầng này - KHÔNG được coi là "ai cũng
        biết rồi nên không cần giải thích". Chỉ được bỏ qua giải thích với
        các từ thuộc vốn từ phổ thông hàng ngày (ví dụ: "báo cáo", "kế
        hoạch", "yêu cầu", "thực hiện").
      + Trước khi viết xong đoạn thuộc tầng này, hãy tự hỏi: "nếu một người
        chưa từng làm việc trong cơ quan nhà nước đọc câu này, họ có hiểu hết
        từng cụm từ không?" - nếu có bất kỳ cụm nào còn nghi ngờ, PHẢI thêm
        giải thích.

    - TÍNH BAO QUÁT:
      + Bản tóm tắt phải phản ánh đầy đủ các nhóm nội dung chính của văn bản.
      + Nếu văn bản gồm nhiều mục thì cần bao quát tất cả các mục quan trọng theo đúng thứ tự.
      + Không được chỉ tóm tắt phần mở đầu hoặc mục đích ban hành rồi kết thúc.
      + Ưu tiên sự đầy đủ và bao quát hơn là rút ngắn tối đa.
    TRƯỚC KHI TRẢ VỀ, tự kiểm tra lại bài viết theo 2 việc sau, rồi mới trả lời:
    1. Nếu phát hiện bất kỳ dòng nào bắt đầu bằng số thứ tự, ký hiệu đánh số,
       hoặc tiêu đề mục tách riêng - PHẢI viết lại đoạn đó thành câu văn xuôi
       liền mạch.
    2. Rà lại TỪNG đoạn ứng với tầng "trung bình" hoặc tầng "nền" (ở style
       "khong_chuyen_mon"/"binh_thuong") - LIỆT KÊ RA TRONG ĐẦU tất cả các
       cụm từ mang tính hành chính/pháp lý/chuyên ngành xuất hiện trong đoạn
       đó (kể cả các cụm nghe quen thuộc như "quy hoạch tổng thể", "xã hội
       hóa", "tinh giản biên chế"...), sau đó kiểm tra từng cụm đã có giải
       thích đi kèm trong câu chưa. Cụm nào còn thiếu, PHẢI bổ sung giải
       thích ngắn gọn trước khi trả về.
    Chỉ trả về bản đã kiểm tra lại theo cả 2 việc trên, không trả về bản nháp.
    """.strip()

    return prompt


# ==== BƯỚC 4: HÀM CHẠY CHÍNH CHO 1 PERSONA ====

async def tom_tat_hanh_chinh_cho_persona(persona, ket_qua_extract, ket_qua_khop_persona, client, semaphore,
                                         model_name=OSS_MODEL_NAME):
    danh_sach_muc = ket_qua_extract.get("danh_sach_muc", [])

    danh_sach_muc_voi_tang, style = gan_tang_do_sau_va_style(
        persona.get("id"), danh_sach_muc, ket_qua_khop_persona
    )

    so_muc_chuyen_sau = sum(1 for m in danh_sach_muc_voi_tang if m["tang_do_sau"] == TANG_CHUYEN_SAU)
    so_muc_trung_binh = sum(1 for m in danh_sach_muc_voi_tang if m["tang_do_sau"] == TANG_TRUNG_BINH)

    prompt = build_hanh_chinh_prompt(persona, ket_qua_extract, danh_sach_muc_voi_tang, style)

    async def _call(prompt_hien_tai):
        async def _goi():
            return await client.models.generate_content(
                model=model_name,
                contents=prompt_hien_tai,
                config={"temperature": 0.0},
            )

        async with semaphore:
            return await retry_generate_async(_goi)

    response = await _call(prompt)
    summary = response.text.strip()

    danh_sach_muc_luu = [
        {
            "heading": m.get("heading"),
            "doan_van": m.get("doan_van", []),
            "tang_do_sau": m["tang_do_sau"],
        }
        for m in danh_sach_muc_voi_tang
    ]

    return {
        "id": persona.get("id"),
        "file": ket_qua_extract.get("file"),
        "style": style,
        "summary": summary,
        "so_muc_chuyen_sau": so_muc_chuyen_sau,
        "so_muc_trung_binh": so_muc_trung_binh,
        "so_muc_tong": len(danh_sach_muc_voi_tang),
        "danh_sach_muc_voi_tang": danh_sach_muc_luu,
    }

if __name__ == "__main__":
    import argparse
    from pipeline.hanhchinh.hanh_chinh_extract import xu_ly_1_file
    from pipeline.hanhchinh.hanh_chinh_persona_match_oss import (
        chay_khop_persona_cho_van_ban,
    )

    parser = argparse.ArgumentParser(description="Tom tat hanh chinh ca nhan hoa cho 1 persona")
    parser.add_argument("--file", required=True, help="duong dan file docx van ban hanh chinh")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="id cua persona, vi du NN0001")
    group.add_argument("--so-luong", type=int, help="chay tu persona dau tien den persona thu n")
    group.add_argument("--tu-id", help="chạy từ persona này (vd NN0018), dùng kèm --den-id")
    parser.add_argument("--den-id", help="id persona kết thúc, dùng kèm --tu-id (vd NN0026)")
    parser.add_argument(
        "--variant",
        type=str,
        default=None,
        help="ten bien the persona, neu co se ghi vao thu muc con rieng de tranh de len du lieu persona day du truong"
    )
    args = parser.parse_args()

    duong_dan_file = Path(args.file)
    if not duong_dan_file.exists():
        duong_dan_file = ROOT_DIR / "data" / "hanh_chinh" / duong_dan_file
    if not duong_dan_file.exists():
        raise SystemExit(f"Không tìm thấy file: {duong_dan_file}")

    EXTRACT_CACHE_DIR = ROOT_DIR / "output" / "hanh_chinh" / "extract"
    MATCH_CACHE_DIR = ROOT_DIR / "output" / "hanh_chinh" / "persona_match"
    SUMMARY_DIR = ROOT_DIR / "output" / "hanh_chinh" / "summary"
    for d in (EXTRACT_CACHE_DIR, MATCH_CACHE_DIR, SUMMARY_DIR):
        d.mkdir(parents=True, exist_ok=True)

    ten_file_goc = duong_dan_file.stem

    extract_cache_path = EXTRACT_CACHE_DIR / f"{ten_file_goc}.json"
    if extract_cache_path.exists():
        with open(extract_cache_path, encoding="utf-8") as f:
            ket_qua_extract = json.load(f)
        print(f"Đã đọc kết quả trích xuất từ cache: {extract_cache_path}")
    else:
        print(f"Đang trích xuất văn bản từ: {duong_dan_file}")
        ket_qua_extract = xu_ly_1_file(str(duong_dan_file))
        with open(extract_cache_path, "w", encoding="utf-8") as f:
            json.dump(ket_qua_extract, f, ensure_ascii=False, indent=2)

    ten_file_persona = f"state_profiles_{args.variant}.json" if args.variant else "state_profiles_nt_nn_tc_kn_cd_ch.json"
    duong_dan_persona = ROOT_DIR / "data" / "profile_variants" / ten_file_persona
    with open(duong_dan_persona, encoding="utf-8") as f:
        personas = json.load(f)
    if args.id:
        personas_can_chay = [p for p in personas if p.get("id") == args.id]
        if not personas_can_chay:
            raise SystemExit(
                f"Không tìm thấy persona có id = {args.id} trong {duong_dan_persona}"
            )
    elif args.tu_id:
        so_tu = int(re.sub(r"\D", "", args.tu_id))
        so_den = int(re.sub(r"\D", "", args.den_id)) if args.den_id else so_tu
        personas_can_chay = [
            p for p in personas
            if so_tu <= int(re.sub(r"\D", "", p.get("id", "0"))) <= so_den
        ]
        if not personas_can_chay:
            raise SystemExit(
                f"Không tìm thấy persona nào trong khoảng {args.tu_id} - {args.den_id or args.tu_id}"
            )
    else:
        personas_can_chay = personas[:args.so_luong]

    if args.variant:
        out_dir = SUMMARY_DIR / args.variant / ten_file_goc
    else:
        out_dir = SUMMARY_DIR / ten_file_goc
    out_dir.mkdir(parents=True, exist_ok=True)

    async def xu_ly_mot_persona(client, semaphore, persona, ket_qua_extract, ket_qua_khop_persona, i, tong):
        out_path_json = out_dir / f"{persona['id']}.json"
        out_path_md = out_dir / f"{persona['id']}.md"

        if out_path_json.exists():
            print(f"[{i}/{tong}] {persona['id']} đã tồn tại -> bỏ qua")
            return

        print(f"\n[{i}/{tong}] Bắt đầu xử lý {persona['id']}...")

        ket_qua = await tom_tat_hanh_chinh_cho_persona(
            persona,
            ket_qua_extract,
            ket_qua_khop_persona,
            client,
            semaphore,
        )

        with open(out_path_json, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)

        with open(out_path_md, "w", encoding="utf-8") as f:
            f.write(ket_qua["summary"])

        print(f"Style: {ket_qua['style']}")
        print(
            f"Chuyên sâu: {ket_qua['so_muc_chuyen_sau']}, "
            f"TB: {ket_qua['so_muc_trung_binh']}"
        )
        print(f"Đã ghi: {out_path_json}")

    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)

        match_cache_path = MATCH_CACHE_DIR / f"{ten_file_goc}.json"
        if match_cache_path.exists():
            with open(match_cache_path, encoding="utf-8") as f:
                ket_qua_khop_persona = json.load(f)
            print(f"Đã đọc kết quả khớp persona từ cache: {match_cache_path}")
        else:
            print("Đang gọi LLM khớp persona theo ngành...")
            ket_qua_khop_persona = await chay_khop_persona_cho_van_ban(client, semaphore, ket_qua_extract)
            with open(match_cache_path, "w", encoding="utf-8") as f:
                json.dump(ket_qua_khop_persona, f, ensure_ascii=False, indent=2)

        tong = len(personas_can_chay)
        tasks = [
            xu_ly_mot_persona(client, semaphore, persona, ket_qua_extract, ket_qua_khop_persona, i, tong)
            for i, persona in enumerate(personas_can_chay, start=1)
        ]
        await asyncio.gather(*tasks)

    asyncio.run(chay())