# Ontology-Driven Multi-Document Summarization with Personas Vietnam
## Sử dụng ontology tóm tắt đa văn bản theo nhân khẩu học Việt Nam

### 1. Giới thiệu / Motivation

#### a) Bối cảnh

Các hệ thống tóm tắt văn bản hiện nay phần lớn sinh ra một bản tóm tắt duy nhất  cho mọi người đọc, bất kể người đó là ai, quan tâm điều gì, hay cần thông tin ở  mức độ chuyên sâu nào. Đề tài này xây dựng một hệ thống tóm tắt **đa văn bản** có khả năng **cá nhân hóa theo persona** — cụ thể là cán bộ/công chức thuộc  các ngành/lĩnh vực khác nhau — nhằm tạo ra bản tóm tắt phù hợp với vai trò và  mối quan tâm của từng người đọc.

Điểm khác biệt của cách tiếp cận trong đề tài là sử dụng **ontology** làm  thành phần trung gian: thay vì đưa thẳng persona và văn bản nguồn vào prompt,  hệ thống truy vấn ontology để lấy ra ngữ cảnh (khái niệm, quan hệ, ngành liên  quan) gắn với persona, từ đó định hướng LLM chọn lọc, sắp xếp và trình bày nội dung tóm tắt.

#### b) Câu hỏi nghiên cứu

Các trường persona (ngành/lĩnh vực, chuyên môn, mối quan tâm) ảnh hưởng như
thế nào đến nội dung và cách trình bày của bản tóm tắt do LLM sinh ra, và
làm sao đánh giá điều đó một cách có hệ thống, có thể tái lặp?

#### c) Giả thuyết nghiên cứu

1. **Chủ đề khớp mối quan tâm persona sẽ được tóm tắt chi tiết hơn theo tỷ lệ** —
   phần nội dung liên quan trực tiếp đến lĩnh vực/mối quan tâm của persona sẽ
   chiếm không gian lớn hơn trong bản tóm tắt so với phần không liên quan.
2. **Khi nội dung nguồn khớp lĩnh vực chuyên môn của persona, tóm tắt sẽ ở
   chế độ chuyên gia** — sử dụng thuật ngữ chuyên ngành, cấu trúc trình bày
   mang tính chuyên môn thay vì phổ thông.

#### d) Phạm vi nhánh này

README này mô tả nhánh xử lý tóm tắt đa văn bản có ứng dụng ontology, bao gồm
3 loại nội dung nguồn: báo chí, hành chính, chính luận — và cách ontology
được dùng để dẫn hướng cá nhân hóa cho từng loại.