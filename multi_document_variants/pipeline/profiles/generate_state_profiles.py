import csv
import json
import random
from collections import Counter
from pathlib import Path

TINH_LIST = ["Bắc Ninh", "Nghệ An", "Khánh Hòa", "An Giang", "Thái Nguyên",
             "Quảng Ninh", "Lâm Đồng", "Đắk Lắk", "Cà Mau", "Hà Tĩnh",
             "Phú Thọ", "Ninh Bình"]
XA_LIST = ["Tân Hồng", "Hưng Đông", "Ninh Thân", "Lương Phi", "Tân Kim",
           "Bình Khê", "Liên Nghĩa", "Cư Elang", "Khánh Bình Tây", "Sơn Tây"]
NUOC_LIST = ["Nhật Bản", "Hàn Quốc", "Pháp", "Đức", "Úc", "Singapore", "Lào", "Campuchia"]
QUANKHU_LIST = ["1", "2", "3", "4", "5", "7", "9"]
VUNGHQ_LIST = ["1", "2", "3", "4", "5"]
KHUVUC_LIST = ["1", "3", "5", "7", "9", "11"]
CUAKHAU_LIST = ["Hữu Nghị", "Lào Cai", "Mộc Bài", "Cầu Treo", "Bờ Y"]
TRUONG_LIST = ["Chuyên Lê Hồng Phong", "Nguyễn Trãi", "Trần Phú", "Lý Thường Kiệt", "Phan Bội Châu"]


def fmt(template, rng):
    if "{" not in template:
        return template
    return template.format(
        tinh=rng.choice(TINH_LIST),
        xa=rng.choice(XA_LIST),
        nuoc=rng.choice(NUOC_LIST),
        quankhu=rng.choice(QUANKHU_LIST),
        vunghq=rng.choice(VUNGHQ_LIST),
        khuvuc=rng.choice(KHUVUC_LIST),
        cuakhau=rng.choice(CUAKHAU_LIST),
        truong=rng.choice(TRUONG_LIST),
        so=rng.randint(1, 99),
    )


TAXONOMY = {
    "Công chức hành chính nhà nước": {
        "chu_de_pool": ["Thời sự / Xã hội", "Chính trị / Pháp luật", "Công nghệ / Kỹ thuật số"],
        "nganh_nho": {
            "Nội vụ": ["Bộ Nội vụ", "Sở Nội vụ tỉnh {tinh}"],
            "Cải cách hành chính": ["Sở Nội vụ tỉnh {tinh} - Phòng Cải cách hành chính",
                                    "Bộ phận Một cửa UBND xã {xa}, tỉnh {tinh}"],
            "Quản lý công vụ": ["Vụ Công chức, viên chức - Bộ Nội vụ", "Sở Nội vụ tỉnh {tinh}"],
            "Thi đua - Khen thưởng": ["Ban Thi đua - Khen thưởng Trung ương",
                                      "Sở Nội vụ tỉnh {tinh} - Phòng Thi đua, Khen thưởng"],
        },
        "cau_hoi_mau": [
            "cập nhật quy định mới về sắp xếp tổ chức bộ máy và tinh giản biên chế",
            "theo dõi tiến độ triển khai mô hình chính quyền địa phương 2 cấp",
            "nắm bắt hướng dẫn thi hành Luật Cán bộ, công chức sửa đổi",
            "cập nhật quy trình một cửa liên thông và chuyển đổi số thủ tục hành chính",
        ],
    },
    "Quân đội": {
        "chu_de_pool": ["Quốc phòng / An ninh", "Thời sự / Xã hội", "Ngoại giao / Quan hệ quốc tế"],
        "nganh_nho": {
            "Lục quân": ["Bộ Tư lệnh Quân khu {quankhu}", "Lữ đoàn Bộ binh {so}, Quân khu {quankhu}"],
            "Hải quân": ["Bộ Tư lệnh Hải quân", "Bộ Tư lệnh Vùng {vunghq} Hải quân"],
            "Không quân": ["Quân chủng Phòng không - Không quân", "Sư đoàn Không quân {so}"],
            "Hậu cần - Kỹ thuật": ["Tổng cục Hậu cần", "Cục Kỹ thuật, Quân khu {quankhu}"],
            "Biên phòng": ["Bộ Tư lệnh Bộ đội Biên phòng", "Bộ Chỉ huy Bộ đội Biên phòng tỉnh {tinh}"],
        },
        "cau_hoi_mau": [
            "theo dõi diễn biến hoạt động huấn luyện, diễn tập trên địa bàn phụ trách",
            "cập nhật chính sách hậu phương quân đội và chế độ đãi ngộ quân nhân",
            "nắm tình hình an ninh biên giới, chủ quyền biển đảo liên quan khu vực đóng quân",
            "cập nhật kế hoạch hợp tác quốc phòng song phương trong năm",
        ],
    },
    "Công an / Cảnh sát": {
        "chu_de_pool": ["Quốc phòng / An ninh", "Chính trị / Pháp luật", "Thời sự / Xã hội"],
        "nganh_nho": {
            "An ninh": ["Cục An ninh nội địa - Bộ Công an", "Công an tỉnh {tinh} - Phòng An ninh nội địa"],
            "Cảnh sát điều tra": ["Công an tỉnh {tinh} - Phòng Cảnh sát điều tra tội phạm",
                                  "Công an xã {xa}, tỉnh {tinh}"],
            "Cảnh sát giao thông": ["Phòng Cảnh sát giao thông Công an tỉnh {tinh}"],
            "Phòng cháy chữa cháy": ["Phòng Cảnh sát PCCC và CNCH Công an tỉnh {tinh}"],
            "Quản lý xuất nhập cảnh": ["Cục Quản lý xuất nhập cảnh - Bộ Công an",
                                       "Công an tỉnh {tinh} - Phòng Quản lý xuất nhập cảnh"],
        },
        "cau_hoi_mau": [
            "theo dõi tình hình trật tự an toàn giao thông và tai nạn giao thông trên địa bàn",
            "cập nhật thủ đoạn tội phạm công nghệ cao, lừa đảo qua mạng để cảnh báo người dân",
            "nắm diễn biến an ninh trật tự dịp cao điểm, lễ hội trên địa bàn quản lý",
            "cập nhật quy định mới về xử phạt vi phạm hành chính trong lĩnh vực phụ trách",
        ],
    },
    "An ninh - Quốc phòng": {
        "chu_de_pool": ["Quốc phòng / An ninh", "Chính trị / Pháp luật",
                        "Ngoại giao / Quan hệ quốc tế", "Công nghệ / Kỹ thuật số"],
        "nganh_nho": {
            "Chiến lược quốc phòng": ["Cục Chiến lược - Bộ Quốc phòng", "Viện Chiến lược Quốc phòng"],
            "Công nghiệp quốc phòng": ["Tổng cục Công nghiệp Quốc phòng"],
            "An ninh mạng quốc gia": ["Ban Chỉ đạo An ninh mạng quốc gia",
                                      "Cục An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao"],
            "Đối ngoại quốc phòng": ["Cục Đối ngoại - Bộ Quốc phòng"],
        },
        "cau_hoi_mau": [
            "theo dõi các báo cáo, phân tích tình hình an ninh khu vực và thế giới liên quan lĩnh vực phụ trách",
            "cập nhật chủ trương, chiến lược quốc phòng mới được ban hành",
            "nắm tiến độ các dự án hợp tác công nghiệp quốc phòng đang triển khai",
            "theo dõi diễn biến an ninh mạng, các sự cố tấn công mạng quy mô lớn gần đây",
        ],
    },
    "Ngoại giao": {
        "chu_de_pool": ["Ngoại giao / Quan hệ quốc tế", "Tài chính / Kế toán", "Chính trị / Pháp luật"],
        "nganh_nho": {
            "Song phương": ["Vụ Khu vực song phương - Bộ Ngoại giao", "Đại sứ quán Việt Nam tại {nuoc}"],
            "Đa phương": ["Vụ các Tổ chức Quốc tế - Bộ Ngoại giao", "Phái đoàn Việt Nam tại Liên Hợp Quốc"],
            "Lãnh sự": ["Cục Lãnh sự - Bộ Ngoại giao", "Tổng Lãnh sự quán Việt Nam tại {nuoc}"],
            "Kinh tế đối ngoại": ["Vụ Tổng hợp Kinh tế - Bộ Ngoại giao", "Sở Ngoại vụ tỉnh {tinh}"],
            "Công tác người Việt Nam ở nước ngoài": ["Ủy ban Nhà nước về người Việt Nam ở nước ngoài"],
        },
        "cau_hoi_mau": [
            "cập nhật diễn biến quan hệ song phương với các đối tác chiến lược",
            "theo dõi lịch trình các hội nghị, diễn đàn đa phương sắp diễn ra",
            "nắm chính sách bảo hộ công dân và hỗ trợ cộng đồng người Việt ở nước ngoài",
            "cập nhật tình hình đàm phán các hiệp định thương mại, đầu tư song phương",
        ],
    },
    "Tài chính - Ngân sách": {
        "chu_de_pool": ["Tài chính / Kế toán", "Chính trị / Pháp luật", "Thời sự / Xã hội"],
        "nganh_nho": {
            "Ngân sách nhà nước": ["Vụ Ngân sách Nhà nước - Bộ Tài chính", "Sở Tài chính tỉnh {tinh}"],
            "Thuế": ["Cục Thuế tỉnh {tinh}", "Chi cục Thuế khu vực {khuvuc}"],
            "Hải quan": ["Chi cục Hải quan cửa khẩu {cuakhau}", "Cục Hải quan tỉnh {tinh}"],
            "Kho bạc Nhà nước": ["Kho bạc Nhà nước tỉnh {tinh}"],
            "Quản lý tài sản công": ["Cục Quản lý Công sản - Bộ Tài chính",
                                     "Sở Tài chính tỉnh {tinh} - Phòng Quản lý giá và Công sản"],
        },
        "cau_hoi_mau": [
            "cập nhật quy định mới về định mức phân bổ ngân sách và chi thường xuyên",
            "theo dõi tiến độ giải ngân vốn đầu tư công của địa phương/đơn vị",
            "nắm chính sách thuế mới ban hành áp dụng cho doanh nghiệp và hộ kinh doanh",
            "cập nhật quy trình kê khai, quyết toán thuế điện tử",
        ],
    },
    "Ngân hàng - Tiền tệ": {
        "chu_de_pool": ["Tài chính / Kế toán", "Công nghệ / Kỹ thuật số"],
        "nganh_nho": {
            "Chính sách tiền tệ": ["Vụ Chính sách tiền tệ - Ngân hàng Nhà nước Việt Nam"],
            "Giám sát ngân hàng": ["Cơ quan Thanh tra, Giám sát ngân hàng - NHNN"],
            "Thanh toán": ["Vụ Thanh toán - Ngân hàng Nhà nước Việt Nam"],
            "Quản lý ngoại hối": ["Vụ Quản lý Ngoại hối - Ngân hàng Nhà nước Việt Nam",
                                  "Ngân hàng Nhà nước - Chi nhánh Khu vực {khuvuc}"],
        },
        "cau_hoi_mau": [
            "theo dõi diễn biến lãi suất điều hành và tác động đến thị trường tín dụng",
            "cập nhật biến động tỷ giá và chính sách quản lý ngoại hối",
            "nắm tình hình nợ xấu và các biện pháp giám sát an toàn hệ thống ngân hàng",
            "theo dõi lộ trình triển khai các quy định mới về thanh toán không dùng tiền mặt",
        ],
    },
    "Tư pháp - Pháp luật": {
        "chu_de_pool": ["Chính trị / Pháp luật", "Thời sự / Xã hội"],
        "nganh_nho": {
            "Xét xử": ["Tòa án nhân dân tỉnh {tinh}"],
            "Kiểm sát": ["Viện kiểm sát nhân dân tỉnh {tinh}"],
            "Thi hành án": ["Phòng Thi hành án dân sự tỉnh {tinh}"],
            "Xây dựng pháp luật": ["Vụ Các vấn đề chung về xây dựng pháp luật - Bộ Tư pháp"],
            "Công chứng - Hộ tịch": ["Sở Tư pháp tỉnh {tinh}"],
        },
        "cau_hoi_mau": [
            "cập nhật các luật, nghị định mới có hiệu lực liên quan lĩnh vực phụ trách",
            "theo dõi án lệ và các vụ việc điển hình được dư luận quan tâm",
            "nắm tiến độ thi hành án và các vướng mắc phát sinh trong thực tiễn",
            "cập nhật quy định mới về công chứng, hộ tịch điện tử",
        ],
    },
    "Y tế": {
        "chu_de_pool": ["Y tế / Chăm sóc", "Thời sự / Xã hội", "Chính trị / Pháp luật"],
        "nganh_nho": {
            "Khám chữa bệnh": ["Bệnh viện Đa khoa tỉnh {tinh}"],
            "Y tế dự phòng": ["Trung tâm Kiểm soát bệnh tật (CDC) tỉnh {tinh}",
                              "Trạm Y tế xã {xa}, tỉnh {tinh}"],
            "Dược - Trang thiết bị y tế": ["Sở Y tế tỉnh {tinh} - Phòng Nghiệp vụ Dược"],
            "Bảo hiểm y tế": ["Bảo hiểm xã hội tỉnh {tinh}"],
        },
        "cau_hoi_mau": [
            "theo dõi diễn biến dịch bệnh theo mùa và khuyến cáo phòng chống",
            "cập nhật chính sách bảo hiểm y tế và mức hưởng mới",
            "nắm quy định mới về quản lý dược phẩm, trang thiết bị y tế",
            "theo dõi tình hình nhân lực và cơ sở vật chất y tế tuyến cơ sở",
        ],
    },
    "Giáo dục - Đào tạo": {
        "chu_de_pool": ["Giáo dục", "Thời sự / Xã hội", "Công nghệ / Kỹ thuật số"],
        "nganh_nho": {
            "Giáo dục phổ thông": ["Sở Giáo dục và Đào tạo tỉnh {tinh}", "Trường THPT {truong}, tỉnh {tinh}"],
            "Giáo dục đại học": ["Vụ Giáo dục Đại học - Bộ Giáo dục và Đào tạo"],
            "Giáo dục nghề nghiệp": ["Trường Cao đẳng nghề tỉnh {tinh}"],
            "Quản lý nhà giáo": ["Sở Giáo dục và Đào tạo tỉnh {tinh} - Phòng Tổ chức cán bộ"],
        },
        "cau_hoi_mau": [
            "cập nhật lịch thi, quy chế tuyển sinh và kỳ thi tốt nghiệp THPT",
            "theo dõi chính sách đổi mới chương trình giáo dục phổ thông",
            "nắm quy định mới về chế độ, chính sách đối với nhà giáo",
            "cập nhật thông tin tuyển sinh đại học, cao đẳng năm nay",
        ],
    },
    "Khoa học - Công nghệ - TT&TT": {
        "chu_de_pool": ["Công nghệ / Kỹ thuật số", "Tài chính / Kế toán", "Chính trị / Pháp luật"],
        "nganh_nho": {
            "Chuyển đổi số": ["Sở Thông tin và Truyền thông tỉnh {tinh}"],
            "An toàn thông tin": ["Cục An toàn thông tin - Bộ Khoa học và Công nghệ"],
            "Viễn thông": ["Sở Thông tin và Truyền thông tỉnh {tinh} - Phòng Viễn thông"],
            "Nghiên cứu khoa học - Đổi mới sáng tạo": ["Sở Khoa học và Công nghệ tỉnh {tinh}"],
        },
        "cau_hoi_mau": [
            "theo dõi tiến độ triển khai đề án chuyển đổi số của địa phương/đơn vị",
            "cập nhật cảnh báo về lỗ hổng bảo mật, sự cố an toàn thông tin",
            "nắm chính sách hỗ trợ doanh nghiệp khởi nghiệp đổi mới sáng tạo",
            "theo dõi xu hướng công nghệ mới (AI, dữ liệu lớn) áp dụng trong quản lý nhà nước",
        ],
    },
    "Nông nghiệp - Tài nguyên - Môi trường": {
        "chu_de_pool": ["Môi trường", "Tài chính / Kế toán", "Thời sự / Xã hội"],
        "nganh_nho": {
            "Nông nghiệp - Phát triển nông thôn": ["Sở Nông nghiệp và Môi trường tỉnh {tinh}"],
            "Đất đai": ["Văn phòng Đăng ký đất đai tỉnh {tinh}"],
            "Môi trường": ["Sở Nông nghiệp và Môi trường tỉnh {tinh} - Chi cục Bảo vệ Môi trường"],
            "Tài nguyên nước - Khí tượng": ["Đài Khí tượng Thủy văn khu vực {khuvuc}"],
        },
        "cau_hoi_mau": [
            "theo dõi diễn biến thiên tai, thời tiết cực đoan ảnh hưởng sản xuất nông nghiệp",
            "cập nhật quy định mới về quản lý, cấp phép sử dụng đất đai",
            "nắm tình hình xuất khẩu nông sản và các rào cản kỹ thuật thị trường",
            "theo dõi tiến độ xử lý các điểm nóng ô nhiễm môi trường trên địa bàn",
        ],
    },
}

CAP_BAC_BY_KINHNGHIEM = [
    (1, 10, "Chuyên viên"),
    (10, 25, "Chuyên viên chính"),
    (25, 51, "Chuyên viên cao cấp / Lãnh đạo"),
]

CHUC_DANH_BY_CAPBAC = {
    "Chuyên viên": ["Chuyên viên", "Cán bộ", "Nhân viên nghiệp vụ"],
    "Chuyên viên chính": ["Chuyên viên chính", "Phó trưởng phòng", "Trưởng nhóm nghiệp vụ"],
    "Chuyên viên cao cấp / Lãnh đạo": ["Trưởng phòng", "Phó Giám đốc", "Chuyên viên cao cấp"],
}

# cac cau mo dau the hien tinh dinh huong/khuynh huong, khong chi la 1 cau hoi
# hanh chinh kho khan nhu truoc, giup phan biet "thien huong quan tam" cua tung nguoi
CAU_HOI_INTRO = [
    "Có xu hướng ưu tiên theo dõi thông tin liên quan đến việc {noi_dung}.",
    "Luôn dành sự quan tâm sát sao đến việc {noi_dung}.",
    "Đặc biệt chú trọng đến việc {noi_dung}.",
    "Có khuynh hướng tập trung nhiều hơn vào việc {noi_dung}.",
]

# thu tu cac truong dung de sinh mo_ta_chung theo cap do (dung cho viec sinh
# nhieu bo du lieu bien the sau nay, moi bo chi lay N truong dau trong danh sach nay)
FIELD_ORDER = ["nganh_to", "nganh_nho", "to_chuc", "kinh_nghiem", "chu_de", "cau_hoi_truoc_mat"]


def pick_kinh_nghiem_so_nam(rng):
    return rng.randint(1, 50)


def cap_bac_tu_so_nam(so_nam):
    for lo, hi, cb in CAP_BAC_BY_KINHNGHIEM:
        if lo <= so_nam < hi:
            return cb
    return CAP_BAC_BY_KINHNGHIEM[-1][2]


def pick_do_tuoi(so_nam, rng):
    return min(80, max(24, 22 + so_nam + rng.randint(0, 6)))


def tao_kinh_nghiem_text(so_nam, chuc_danh, nganh_nho):
    return f"{so_nam} năm kinh nghiệm công tác trong lĩnh vực {nganh_nho}, hiện đang đảm nhiệm vị trí {chuc_danh}."


def pick_chu_de(chu_de_pool, rng):
    chinh = chu_de_pool[0]
    phu_con_lai = chu_de_pool[1:]
    so_luong_them = rng.randint(1, min(2, len(phu_con_lai))) if phu_con_lai else 0
    them = rng.sample(phu_con_lai, so_luong_them) if so_luong_them else []
    return [chinh] + them


def tao_cau_hoi_truoc_mat(cau_hoi_mau, rng):
    noi_dung = rng.choice(cau_hoi_mau)
    intro = rng.choice(CAU_HOI_INTRO)
    return intro.format(noi_dung=noi_dung)


def build_mo_ta_chung(data, gioi_tinh, so_truong=None, truong_list=None):
    if truong_list is not None:
        truong_dung = truong_list
    else:
        if so_truong is None:
            so_truong = len(FIELD_ORDER)
        truong_dung = FIELD_ORDER[:so_truong]

    nguoi_tu = "người phụ nữ" if gioi_tinh == "Nữ" else "người đàn ông"
    cau = "Một " + nguoi_tu
    if "nganh_to" in truong_dung:
        cau += " công tác trong lĩnh vực " + data["nganh_to"]
    if "nganh_nho" in truong_dung:
        cau += ", chuyên trách mảng " + data["nganh_nho"]
    if "to_chuc" in truong_dung:
        cau += ", hiện làm việc tại " + data["to_chuc"]
    cau += "."

    if "kinh_nghiem" in truong_dung:
        cau += " " + data["kinh_nghiem"]
    if "chu_de" in truong_dung:
        cau += " Quan tâm chính đến các chủ đề: " + ", ".join(data["chu_de"]) + "."
    if "cau_hoi_truoc_mat" in truong_dung:
        cau += " " + data["cau_hoi_truoc_mat"]

    return cau


def build_profile(idx, nganh_to, gioi_tinh, rng, nganh_nho=None):
    info = TAXONOMY[nganh_to]
    if nganh_nho is None:
        nganh_nho = rng.choice(list(info["nganh_nho"].keys()))
    to_chuc_template = rng.choice(info["nganh_nho"][nganh_nho])
    to_chuc = fmt(to_chuc_template, rng)

    so_nam = pick_kinh_nghiem_so_nam(rng)
    cap_bac = cap_bac_tu_so_nam(so_nam)
    do_tuoi = pick_do_tuoi(so_nam, rng)
    chuc_danh = rng.choice(CHUC_DANH_BY_CAPBAC[cap_bac])
    kinh_nghiem = tao_kinh_nghiem_text(so_nam, chuc_danh, nganh_nho)

    chu_de = pick_chu_de(info["chu_de_pool"], rng)
    cau_hoi_truoc_mat = tao_cau_hoi_truoc_mat(info["cau_hoi_mau"], rng)

    data = {
        "id": f"NN{idx:03d}",
        "nganh_to": nganh_to,
        "nganh_nho": nganh_nho,
        "chu_de": chu_de,
        "cau_hoi_truoc_mat": cau_hoi_truoc_mat,
        "to_chuc": to_chuc,
        "do_tuoi": do_tuoi,
        "kinh_nghiem": kinh_nghiem,
    }
    data["mo_ta_chung"] = build_mo_ta_chung(data, gioi_tinh)
    return data


def generate(n, seed):
    rng = random.Random(seed)
    nganh_list = list(TAXONOMY.keys())
    base = n // len(nganh_list)
    remainder = n % len(nganh_list)
    counts = {nganh: base for nganh in nganh_list}
    for nganh in rng.sample(nganh_list, remainder):
        counts[nganh] += 1

    so_nam_gioi = n // 2
    danh_sach_gioi_tinh = ["Nam"] * so_nam_gioi + ["Nữ"] * (n - so_nam_gioi)
    rng.shuffle(danh_sach_gioi_tinh)

    profiles = []
    idx = 1
    for nganh_to, count in counts.items():
        for _ in range(count):
            gioi_tinh = danh_sach_gioi_tinh[idx - 1]
            profiles.append(build_profile(idx, nganh_to, gioi_tinh, rng))
            idx += 1

    rng.shuffle(profiles)
    for i, p in enumerate(profiles, start=1):
        p["id"] = f"NN{i:04d}"
    return profiles, Counter(danh_sach_gioi_tinh)


def save_json(profiles, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def save_csv(profiles, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "mo_ta_chung", "nganh_to", "nganh_nho", "chu_de",
            "cau_hoi_truoc_mat", "to_chuc", "do_tuoi", "kinh_nghiem",
        ])
        for p in profiles:
            writer.writerow([
                p["id"], p["mo_ta_chung"], p["nganh_to"], p["nganh_nho"],
                " | ".join(p["chu_de"]), p["cau_hoi_truoc_mat"],
                p["to_chuc"], p["do_tuoi"], p["kinh_nghiem"],
            ])


def validate_against_genres(profiles, genres_json_path):
    with open(genres_json_path, encoding="utf-8") as f:
        valid_genres = set(json.load(f)["genres"].keys())
    used = set()
    for p in profiles:
        used.update(p["chu_de"])
    missing = used - valid_genres
    if missing:
        raise ValueError(f"chu_de không khớp article_genres.json: {missing}")
    return True


if __name__ == "__main__":
    N = 60
    SEED = 42
    OUT_NAME = "state_profiles"

    ROOT_DIR = Path(__file__).resolve().parents[3]

    MD_ROOT = ROOT_DIR / "multi_document_variants"
    SHARED_ROOT = ROOT_DIR / "shared"

    DATA_DIR = MD_ROOT / "data" / "profile"
    GENRES_JSON = SHARED_ROOT / "config" / "article_genres.json"

    OUT_JSON = DATA_DIR / f"{OUT_NAME}.json"
    OUT_CSV = DATA_DIR / f"{OUT_NAME}.csv"

    profiles, dem_gioi_tinh = generate(N, SEED)
    save_json(profiles, OUT_JSON)
    save_csv(profiles, OUT_CSV)
    print(f"Đã sinh {len(profiles)} profile -> {OUT_JSON} / {OUT_CSV}")
    print("Kiểm tra cân bằng giới tính trong văn phong mô tả:", dict(dem_gioi_tinh))

    try:
        validate_against_genres(profiles, GENRES_JSON)
        print("Đối chiếu chu_de với article_genres.json: OK")
    except FileNotFoundError:
        print(f"(Bỏ qua đối chiếu genre: không tìm thấy {GENRES_JSON})")
    except ValueError as e:
        print(f"CẢNH BÁO: {e}")

    dist = Counter(p["nganh_to"] for p in profiles)
    for k, v in dist.items():
        print(f"  {k}: {v}")