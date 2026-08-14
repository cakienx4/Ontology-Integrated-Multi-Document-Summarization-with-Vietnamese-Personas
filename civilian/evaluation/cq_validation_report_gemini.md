# Báo cáo validate Competency Questions (CQ)

Thời gian sinh: 2026-07-13 16:39:59
Model tóm tắt: `gemini-3.1-flash-lite` | Model judge: `gemini-3.1-flash-lite`

## Tổng quan
- Tổng số CQ: 20
- PASS: 20 | FAIL: 0 | UNCLEAR: 0 | ERROR: 0

| CQ | Verdict | Confidence | Trường kiểm tra |
|---|---|---|---|
| CQ1 | PASS | 0.95 | education_level (HARD) |
| CQ2 | PASS | 0.95 | occupation + professional_persona (HARD) |
| CQ3 | PASS | 1.0 | age (HARD) |
| CQ4 | PASS | 1.0 | zone (SOFT, bổ trợ) |
| CQ5 | PASS | 0.95 | hobbies_and_interests (SOFT) + education_level (HARD) |
| CQ6 | PASS | 0.95 | career_goals_and_ambitions (GENERAL) |
| CQ7 | PASS | 0.95 | marital_status (SOFT) |
| CQ8 | PASS | 1.0 | skills_and_expertise (HARD) |
| CQ9 | PASS | 0.95 | region (GENERAL) |
| CQ10 | PASS | 1.0 | travel_persona (SOFT) |
| CQ11 | PASS | 1.0 | occupation/professional_persona (HARD) x arts_persona (SOFT) |
| CQ12 | PASS | 0.95 | sports_persona (SOFT) |
| CQ13 | PASS | 0.95 | sex |
| CQ14 | PASS | 1.0 | country (HARD, cố định) |
| CQ15 | PASS | 1.0 | persona (GENERAL) |
| CQ16 | PASS | 1.0 | cultural_background (GENERAL) |
| CQ17 | PASS | 0.95 | zone + occupation (HARD) vs travel_persona (SOFT) - quan hệ uu_tien_hon |
| CQ18 | PASS | 0.95 | occupation x zone (HARD x SOFT combo) |
| CQ19 | PASS | 1.0 | arts_persona (SOFT) |
| CQ20 | PASS | 1.0 | hobbies_and_interests (SOFT) |


---
## CQ1: Trình độ học vấn của người dùng có ảnh hưởng đến độ phức tạp ngôn ngữ trong bản tóm tắt không?
**Trường kiểm tra:** education_level (HARD)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Bà Nga dùng câu ngắn, từ ngữ đời thường, không thuật ngữ; tóm tắt cho Oanh có thể dùng câu phức tạp hơn, lập luận nhiều tầng hơn rõ rệt.

### Person A — Bà Nga - Không học vấn, 88 tuổi
```
Bà con ở Đà Nẵng cần chú ý, ngoài khơi Thái Bình Dương đang có siêu bão Ba Vì rất mạnh. Theo dự báo, bão này ít khả năng đi thẳng vào Biển Đông, nhưng từ ngày 9 đến 11/7, hoàn lưu bão có thể làm gió mùa tây nam mạnh lên.

Vùng biển từ Bắc vào Nam Biển Đông, bao gồm cả Hoàng Sa và Trường Sa, sẽ có gió mạnh cấp 6-7 và sóng cao từ 3 đến 5 mét, biển động rất dữ dội. Các khu vực khác như Quảng Ninh cũng từng chịu ảnh hưởng của bão gây thiệt hại tài sản. Dù mùa bão năm nay được dự báo ít hơn mọi năm, nhưng thời tiết rất khó lường, bà con nên theo dõi tin tức thường xuyên để giữ an toàn cho bản thân và gia đình.
```

### Person B — Oanh - Sau đại học, nhà nghiên cứu
```
Siêu bão Ba Vì (cấp 17, sức gió 200-280 km/h) đang hoạt động tại tây bắc Thái Bình Dương. Theo nhận định từ Trung tâm Dự báo Khí tượng Thủy văn quốc gia và các đài khí tượng quốc tế, xác suất bão đi vào Biển Đông dưới 10%. Tuy nhiên, hoàn lưu bão có khả năng gây ảnh hưởng đến vùng biển phía đông bắc khu vực Bắc Biển Đông từ ngày 9 đến 11/7. Đặc biệt, hiệu ứng hút gió từ siêu bão sẽ làm gió mùa tây nam mạnh lên, gây biển động rất mạnh với gió cấp 6-7 và sóng cao 3-5 m tại khu vực Biển Đông, bao gồm vùng biển quần đảo Hoàng Sa và Trường Sa.

Đối với các khu vực khác, bão Maysak trước đó đã gây thiệt hại khoảng 20 tỷ đồng tại Quảng Ninh. Dự báo mùa mưa bão năm 2026 có số lượng bão và áp thấp nhiệt đới thấp hơn trung bình nhiều năm, song diễn biến vẫn khó lường do tác động của biến đổi khí hậu.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản A sử dụng ngôn ngữ bình dân, câu ngắn và tránh thuật ngữ chuyên môn, phù hợp với đối tượng người cao tuổi. Bản B sử dụng thuật ngữ kỹ thuật (cấp bão, số liệu cụ thể, hiệu ứng khí tượng) và cấu trúc lập luận phức tạp hơn, phản ánh đúng kỳ vọng về sự cá nhân hóa theo trình độ học vấn.


---
## CQ2: Nghề nghiệp và lĩnh vực làm việc của người dùng có quyết định chủ đề văn bản nào được ưu tiên tóm tắt không?
**Trường kiểm tra:** occupation + professional_persona (HARD)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Minh nhấn vào giá vé, chi phí, cơ hội kinh doanh dịch vụ du lịch quanh lễ hội; tóm tắt cho Hiếu có thể trung lập hơn hoặc nhấn khía cạnh khác (không nhất thiết nhấn kinh doanh).

### Person A — Minh - Buôn bán lúa gạo
```
Siêu bão Ba Vì đang ở ngoài khơi xa, cách Philippines rất xa. Các đài dự báo quốc tế đều nhận định bão này không đi vào Biển Đông, khả năng vào chỉ dưới 10%.

Dù bão không vào, nhưng từ ngày 9 đến 11/7, hoàn lưu bão có thể làm gió mùa tây nam mạnh lên. Vùng biển Bắc Biển Đông, Hoàng Sa và Trường Sa sẽ có gió mạnh cấp 6-7, sóng cao từ 3 đến 5 mét, biển động rất mạnh. Anh em làm nghề buôn bán, vận chuyển hàng hóa trên biển cần chú ý theo dõi thời tiết để đảm bảo an toàn cho tàu thuyền và hàng hóa.

Các khu vực khác ngoài Biển Đông chỉ chịu ảnh hưởng gián tiếp.

Mùa bão năm nay dự báo ít bão hơn mọi năm, nhưng thời tiết giờ khó lường, anh em vẫn nên cẩn thận, theo dõi tin tức thường xuyên để chủ động trong việc kinh doanh.
```

### Person B — Dương Xuân Hiếu - Y tế / dược
```
Siêu bão Ba Vì (cấp 17, sức gió 200-280 km/h) đang hoạt động tại tây bắc Thái Bình Dương. Các đài khí tượng quốc tế nhận định xác suất bão đi vào Biển Đông dưới 10%. Tuy nhiên, từ ngày 9-11/7, hoàn lưu bão và hiệu ứng hút gió sẽ làm gió mùa tây nam mạnh lên, gây gió cấp 6-7 và sóng cao 3-5 m tại khu vực Bắc Biển Đông, quần đảo Hoàng Sa và Trường Sa.

Đối với các khu vực khác như Quảng Ninh, bão Maysak trước đó đã gây thiệt hại khoảng 20 tỷ đồng. Dự báo mùa bão năm 2026 có số lượng bão thấp hơn trung bình nhiều năm, nhưng diễn biến vẫn khó lường do biến đổi khí hậu.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A tập trung vào các cảnh báo rủi ro cho vận chuyển hàng hóa và nhấn mạnh việc chủ động trong kinh doanh, rất phù hợp với người làm nghề buôn bán. Bản tóm tắt B cung cấp thông tin mang tính chuyên môn, dữ liệu thiệt hại kinh tế và diễn biến khí hậu, phù hợp với góc nhìn trung lập hoặc quản lý rủi ro của người làm y tế/dược. Sự khác biệt về trọng tâm nội dung phản ánh đúng kỳ vọng cá nhân hóa theo nghề nghiệp.


---
## CQ3: Độ tuổi của người dùng có làm thay đổi chủ đề được nhấn mạnh trong bản tóm tắt không?
**Trường kiểm tra:** age (HARD)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Phương Hạnh (trẻ) có thể nhấn cơ hội/khởi đầu tập luyện cơ bản; tóm tắt cho Bà Nga nhấn mạnh khía cạnh sức khỏe, vận động nhẹ nhàng, an toàn cho người lớn tuổi.

### Person A — Phương Hạnh - 21 tuổi, thất nghiệp tìm việc
```
Hội thảo y tế gần đây nhấn mạnh giai đoạn 40–60 tuổi là thời điểm then chốt để tầm soát bệnh mạn tính và điều chỉnh lối sống. Dù bạn đang ở độ tuổi 21, việc hiểu rõ các nguyên tắc chăm sóc sức khỏe từ sớm là cần thiết để phòng ngừa biến chứng lâu dài.

Các chuyên gia đưa ra những khuyến nghị chính sau:

*   **Tim mạch:** Các bệnh như tăng huyết áp và mỡ máu là nguyên nhân gây biến cố tim mạch hàng đầu. Việc kiểm tra định kỳ các chỉ số huyết áp, cholesterol, đường huyết và duy trì vận động ít nhất 150 phút mỗi tuần là biện pháp phòng ngừa hiệu quả.
*   **Xương khớp:** Tình trạng thoái hóa và loãng xương tăng dần theo tuổi tác. Để duy trì hệ vận động khỏe mạnh, cần bổ sung đủ canxi, vitamin D và thực hiện các bài tập tăng cường sức mạnh cơ bắp.
*   **Ung bướu:** Tầm soát sớm đóng vai trò quyết định trong điều trị. Mọi người cần tuân thủ lịch tầm soát dựa trên độ tuổi và tiền sử gia đình thay vì chỉ dựa vào giới tính.
*   **Bệnh chuyển hóa:** Tình trạng thừa cân, béo phì và đái tháo đường đang gia tăng. Giải pháp cốt lõi là duy trì chế độ ăn cân đối, hạn chế thực phẩm chế biến sẵn, đồ uống nhiều đường, ngủ đủ giấc và kiểm soát cân nặng.

Nhìn chung, các chuyên gia khuyến khích kết hợp khám sức khỏe định kỳ, dinh dưỡng hợp lý và vận động thường xuyên thay vì chỉ tập trung vào một bệnh lý cụ thể. Các nội dung chuyên sâu về sự khác biệt bệnh lý giữa nam và nữ ở độ tuổi trung niên chỉ mang tính chất tham khảo chung.
```

### Person B — Bà Nga - 88 tuổi, nghỉ hưu
```
Các bác sĩ khuyên người lớn tuổi cần chú ý chăm sóc sức khỏe để sống vui khỏe, độc lập.

Về tim mạch, phụ nữ sau mãn kinh có nguy cơ cao hơn, nên cần kiểm tra huyết áp, đường huyết và mỡ máu thường xuyên. Việc vận động nhẹ nhàng hàng ngày rất tốt cho sức khỏe.

Về xương khớp, người lớn tuổi dễ bị loãng xương và thoái hóa khớp. Bà cần ăn uống đủ chất, bổ sung canxi và vitamin D để xương chắc khỏe, tránh té ngã.

Về các bệnh chuyển hóa như tiểu đường hay gan nhiễm mỡ, bà nên ăn uống điều độ, hạn chế đồ ngọt và thực phẩm chế biến sẵn. Ngủ đủ giấc và đi khám định kỳ là cách tốt nhất để phát hiện bệnh sớm.

Các vấn đề về ung bướu hay bệnh lý ở nam giới chỉ là thông tin tham khảo chung. Quan trọng nhất là bà nên đi khám sức khỏe định kỳ theo hướng dẫn của bác sĩ tại địa phương để giữ gìn sức khỏe, an tâm vui vầy cùng con cháu.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt B đã điều chỉnh nội dung phù hợp với người cao tuổi bằng cách nhấn mạnh vào sự an toàn (tránh té ngã), vận động nhẹ nhàng và mục tiêu sống vui khỏe, độc lập. Ngược lại, bản A tập trung vào việc phòng ngừa sớm và xây dựng nền tảng sức khỏe cho người trẻ, phản ánh đúng sự khác biệt về nhu cầu theo độ tuổi như kỳ vọng.


---
## CQ4: Khu vực sống (Đô Thị/Nông Thôn) có làm thay đổi phần nào của văn bản được giữ lại trong tóm tắt không?
**Trường kiểm tra:** zone (SOFT, bổ trợ)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Chị Mai (nông thôn) giữ lại phần giá nông sản/kênh phân phối truyền thống; tóm tắt cho Thảo (đô thị) giữ lại phần thương mại điện tử/logistics.

### Person A — Chị Mai - Buôn bán, Nông Thôn, Đà Nẵng
```
Việc tiêu thụ nông sản hiện nay đang kết hợp giữa kênh truyền thống và nền tảng số. Đối với người làm kinh doanh tại nông thôn như chị, các kênh truyền thống như thương lái, hợp tác xã và chợ đầu mối vẫn giữ vai trò chủ chốt. Những kênh này giúp thu mua nông sản ngay tại chỗ, giảm chi phí vận chuyển và đảm bảo đầu ra ổn định cho các hộ sản xuất nhỏ lẻ mà không đòi hỏi quy trình công nghệ phức tạp. Các địa phương cũng đang tập trung nâng cấp hệ thống chợ đầu mối và trung tâm thu gom để nâng cao năng lực bảo quản, giúp ổn định giá cả và giảm thất thoát sau thu hoạch.

Tại các đô thị lớn, người tiêu dùng đang chuyển sang mua sắm qua sàn thương mại điện tử và ứng dụng trực tuyến, đòi hỏi sự đầu tư vào kho lạnh, logistics và công nghệ truy xuất nguồn gốc bằng mã QR. Tuy nhiên, việc áp dụng thương mại điện tử tại nông thôn vẫn gặp khó khăn do hạ tầng internet và dịch vụ vận chuyển chưa đồng bộ.

Hướng đi phù hợp nhất hiện nay là mô hình kết hợp: hợp tác xã và thương lái đảm nhận khâu thu gom, sơ chế tại vùng sản xuất, còn các sàn thương mại điện tử và doanh nghiệp logistics thực hiện phân phối đến người tiêu dùng. Sự phối hợp này giúp nâng cao giá trị nông sản và tăng thu nhập cho người sản xuất.
```

### Person B — Phạm Thị Thảo - Buôn bán, Đô Thị, TP.HCM
```
Hoạt động tiêu thụ nông sản hiện nay đang chuyển dịch theo mô hình kết hợp giữa kênh truyền thống và thương mại điện tử.

Tại các đô thị lớn như TP.HCM, hành vi tiêu dùng đã thay đổi rõ rệt khi khách hàng ưu tiên đặt mua nông sản qua các sàn thương mại điện tử và ứng dụng trực tuyến. Sự phát triển này đòi hỏi doanh nghiệp phải đầu tư mạnh vào hạ tầng logistics (kho lạnh, trung tâm phân phối, giao hàng nhanh) và áp dụng công nghệ truy xuất nguồn gốc bằng mã QR để đảm bảo chất lượng sản phẩm. Các nền tảng số hiện cung cấp công cụ phân tích nhu cầu thị trường, dự báo sức mua và quản lý đơn hàng theo thời gian thực, giúp tối ưu hóa lượng hàng tồn kho, giảm chi phí vận hành và nâng cao hiệu quả phân phối.

Tại các vùng sản xuất nông nghiệp, mạng lưới phân phối truyền thống thông qua thương lái và hợp tác xã vẫn đóng vai trò chủ chốt trong việc thu gom, sơ chế và tập trung nguồn hàng nhờ quy trình đơn giản, chi phí thấp. Các địa phương đang tiếp tục nâng cấp hệ thống chợ đầu mối và trung tâm thu gom để ổn định giá cả và hỗ trợ nông dân.

Việc kết hợp giữa hệ thống thu mua truyền thống tại vùng sản xuất và các nền tảng phân phối hiện đại tại đô thị là hướng đi tối ưu để nâng cao giá trị nông sản, mở rộng thị trường và tạo chuỗi cung ứng bền vững. Các chương trình hỗ trợ hiện nay đang tập trung đào tạo kỹ năng số và xây dựng thương hiệu cho nông sản để nông dân có thể tham gia hiệu quả hơn vào chuỗi giá trị này.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A tập trung sâu vào vai trò của thương lái, hợp tác xã và chợ đầu mối phù hợp với bối cảnh nông thôn của chị Mai. Bản tóm tắt B nhấn mạnh vào hạ tầng logistics, sàn thương mại điện tử và công nghệ quản lý đơn hàng, phản ánh đúng nhu cầu và bối cảnh đô thị của Thảo. Sự phân bổ nội dung hoàn toàn khớp với kỳ vọng về cá nhân hóa theo khu vực sống.


---
## CQ5: Sở thích cá nhân có đủ để xác định góc độ tóm tắt phù hợp không, hay cần kết hợp với education_level?
**Trường kiểm tra:** hobbies_and_interests (SOFT) + education_level (HARD)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Dù cả hai đều có liên quan đến thể thao trong hồ sơ, văn phong tóm tắt cho A vẫn đơn giản hơn B do chênh lệch education_level, chứng tỏ hobbies không tự quyết định toàn bộ cách diễn đạt.

### Person A — Lê Văn Dung - Công nhân, Trung cấp/Cao đẳng
```
Giai đoạn 40–60 tuổi là thời điểm then chốt để tầm soát bệnh mạn tính và điều chỉnh lối sống nhằm ngăn ngừa biến chứng. Đối với nam giới, việc chủ động theo dõi sức khỏe là cần thiết để duy trì khả năng làm việc và chất lượng cuộc sống lâu dài.

Về tim mạch, nam giới có nguy cơ mắc bệnh sớm hơn, bao gồm tăng huyết áp, rối loạn mỡ máu và bệnh động mạch vành. Bạn cần kiểm tra định kỳ các chỉ số huyết áp, cholesterol, đường huyết và duy trì vận động ít nhất 150 phút mỗi tuần. Đối với hệ xương khớp, dù loãng xương thường được nhắc đến ở nữ giới, nam giới lớn tuổi vẫn đối mặt với nguy cơ gãy xương do giảm mật độ xương. Việc bổ sung canxi, vitamin D và tập luyện kháng lực là cần thiết để duy trì khối cơ và sức khỏe vận động.

Trong lĩnh vực ung bướu, nam giới có tỷ lệ mắc ung thư phổi và ung thư gan cao hơn, do đó cần tuân thủ lịch tầm soát dựa trên độ tuổi và yếu tố nguy cơ cá nhân. Về các bệnh chuyển hóa như đái tháo đường típ 2, béo phì và gan nhiễm mỡ, nam giới thường có xu hướng mắc hội chứng chuyển hóa ở độ tuổi sớm hơn. Để kiểm soát, bạn cần duy trì chế độ ăn cân đối, hạn chế thực phẩm chế biến sẵn, đồ uống nhiều đường, ngủ đủ giấc và kiểm soát cân nặng.

Các vấn đề sức khỏe ở nữ giới và các vùng miền khác chỉ là những biến đổi sinh học hoặc địa lý phụ trợ, không phải trọng tâm ưu tiên trong kế hoạch chăm sóc sức khỏe của bạn.
```

### Person B — Dương Xuân Hiếu - Y tế/dược, Sau đại học
```
Hội thảo khoa học về chăm sóc sức khỏe người trung niên (40–60 tuổi) nhấn mạnh tầm quan trọng của việc phát hiện sớm bệnh mạn tính thông qua khám định kỳ, dinh dưỡng và vận động.

Về tim mạch, tăng huyết áp, rối loạn mỡ máu và bệnh động mạch vành là các nguyên nhân hàng đầu gây biến cố. Nam giới có nguy cơ mắc bệnh sớm hơn, đòi hỏi kiểm soát chặt chẽ huyết áp, cholesterol, đường huyết và duy trì vận động tối thiểu 150 phút/tuần.

Đối với xương khớp, nam giới lớn tuổi cần chú ý nguy cơ gãy xương do giảm mật độ xương. Khuyến nghị bổ sung canxi, vitamin D và tập luyện kháng lực để duy trì khối cơ và sức khỏe hệ vận động.

Trong lĩnh vực ung bướu, tầm soát sớm là yếu tố quyết định tiên lượng. Nam giới cần lưu ý tỷ lệ mắc ung thư phổi và ung thư gan cao hơn, đồng thời tuân thủ lịch tầm soát dựa trên độ tuổi và tiền sử cá nhân.

Về bệnh chuyển hóa, nam giới có xu hướng mắc hội chứng chuyển hóa (thừa cân, béo phì, đái tháo đường típ 2, gan nhiễm mỡ) ở độ tuổi sớm hơn. Giải pháp cốt lõi bao gồm duy trì chế độ ăn cân đối, hạn chế thực phẩm chế biến sẵn, kiểm soát cân nặng và tái khám định kỳ để phát hiện bất thường trước khi có biến chứng.

Các nội dung liên quan đến sức khỏe nữ giới và các vùng miền khác chỉ mang tính chất tham khảo phụ trợ.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A sử dụng ngôn ngữ trực diện, hướng dẫn hành vi cụ thể phù hợp với người lao động, trong khi bản B sử dụng thuật ngữ chuyên môn (tiên lượng, biến cố, hội chứng chuyển hóa) và cấu trúc văn phong học thuật phù hợp với người có trình độ sau đại học. Sự khác biệt này xác nhận rằng education_level đóng vai trò quyết định trong việc điều chỉnh độ phức tạp của ngôn ngữ và lập luận, vượt ra ngoài phạm vi sở thích cá nhân.


---
## CQ6: Mục tiêu nghề nghiệp có làm tăng mức độ ưu tiên của nội dung mang tính định hướng tương lai (xu hướng thị trường, cơ hội đầu tư) trong tóm tắt không?
**Trường kiểm tra:** career_goals_and_ambitions (GENERAL)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Thảo giữ lại phần xu hướng thị trường/thương mại điện tử (cơ hội mở rộng); tóm tắt cho Minh thiên về mô tả hiện trạng giá cả ổn định, ít nhấn cơ hội mở rộng.

### Person A — Trần Thùy Thảo - muốn mở rộng kinh doanh ra quốc tế
```
Việc tiêu thụ nông sản hiện nay đang chuyển dịch theo hướng kết hợp giữa kênh truyền thống và nền tảng số. Đối với người làm kinh doanh tại nông thôn như bạn, mô hình này mang lại nhiều cơ hội tối ưu hóa đầu ra.

Tại các vùng nông thôn như Đồng Nai, mạng lưới phân phối truyền thống thông qua thương lái, hợp tác xã và chợ đầu mối vẫn giữ vai trò chủ chốt. Đây là phương thức phù hợp nhất để thu mua nông sản ngay sau thu hoạch, giúp giảm chi phí vận chuyển, hạn chế thất thoát và đảm bảo đầu ra ổn định cho các hộ sản xuất nhỏ lẻ. Các hợp tác xã hiện nay đóng vai trò quan trọng trong việc hỗ trợ nông dân sơ chế, đóng gói và kết nối với doanh nghiệp. Việc đầu tư nâng cấp hệ thống chợ đầu mối và trung tâm thu gom tại địa phương cũng đang giúp ổn định giá cả và giảm tình trạng được mùa mất giá.

Song song đó, tại các đô thị lớn, người tiêu dùng đang chuyển sang mua sắm qua sàn thương mại điện tử và ứng dụng trực tuyến. Sự phát triển này đòi hỏi đầu tư vào hệ thống logistics, kho lạnh và công nghệ truy xuất nguồn gốc bằng mã QR để đảm bảo chất lượng sản phẩm. Các công cụ số cũng hỗ trợ quản lý đơn hàng, dự báo sức mua và tối ưu hóa tồn kho.

Tuy nhiên, việc ứng dụng thương mại điện tử tại nông thôn vẫn gặp khó khăn do hạ tầng internet, dịch vụ logistics chưa đồng đều và hạn chế về kỹ năng số của người sản xuất. Do đó, hướng đi hiệu quả nhất hiện nay là kết hợp: hợp tác xã và thương lái đảm nhận khâu thu gom, sơ chế tại vùng sản xuất, trong khi các sàn thương mại điện tử và doanh nghiệp logistics chịu trách nhiệm phân phối đến người tiêu dùng đô thị. Sự kết hợp này giúp nâng cao giá trị nông sản và tăng thu nhập cho người sản xuất mà không cần thay thế hoàn toàn các kênh truyền thống.
```

### Person B — Minh - mong muốn ổn định, ít tham vọng mở rộng
```
Việc bán nông sản hiện nay đang có nhiều thay đổi, nhưng cách làm truyền thống vẫn rất quan trọng và phù hợp với người làm nghề như anh.

Tại các vùng nông thôn, việc tiêu thụ qua thương lái, hợp tác xã và chợ đầu mối vẫn là cách tốt nhất. Cách này giúp anh thu mua hàng ngay tại chỗ, giảm chi phí vận chuyển và không phải lo lắng về khâu bảo quản hay công nghệ phức tạp. Các hợp tác xã hiện nay cũng hỗ trợ rất tốt việc phân loại và đóng gói, giúp đầu ra ổn định hơn. Việc địa phương nâng cấp chợ đầu mối và trung tâm thu gom cũng giúp giá cả ổn định, tránh tình trạng được mùa mất giá.

Ở các thành phố lớn, người dân đang chuyển sang mua hàng qua mạng và ứng dụng điện thoại, đòi hỏi hệ thống kho bãi và vận chuyển phải hiện đại hơn. Tuy nhiên, việc bán hàng trực tuyến vẫn còn khó khăn với nhiều nông dân do thiếu kỹ năng công nghệ và hạ tầng chưa đồng bộ.

Hướng đi tốt nhất hiện nay là kết hợp cả hai: anh và các hợp tác xã vẫn giữ vai trò thu gom, sơ chế tại vùng sản xuất, còn các đơn vị vận chuyển và sàn thương mại điện tử sẽ lo khâu đưa hàng đến tay người mua ở thành phố. Sự kết hợp này giúp nông sản bán được giá hơn và mở rộng thị trường, giúp công việc kinh doanh của anh bền vững hơn.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A cho Thảo tập trung vào các từ khóa chiến lược như 'tối ưu hóa đầu ra', 'dự báo sức mua', và 'nâng cao giá trị', phù hợp với mục tiêu mở rộng kinh doanh. Bản tóm tắt B cho Minh nhấn mạnh vào sự 'ổn định', 'không phải lo lắng về công nghệ phức tạp' và 'bền vững', phản ánh đúng kỳ vọng cá nhân hóa theo mục tiêu nghề nghiệp của từng người.


---
## CQ7: Tình trạng hôn nhân có làm thay đổi góc độ được nhấn mạnh khi tóm tắt văn bản về gia đình/du lịch không?
**Trường kiểm tra:** marital_status (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Hoa (đã kết hôn) nhấn vào điểm đến phù hợp gia đình/trẻ nhỏ; tóm tắt cho Hương (ly thân) nhấn vào trải nghiệm cá nhân/độc lập.

### Person A — Huỳnh Thanh Hoa - Đã kết hôn
```
Thị trường du lịch hè năm nay tại Việt Nam đang ghi nhận sự tăng trưởng tích cực với sự phân hóa rõ rệt theo từng nhóm khách hàng.

Đối với nhóm gia đình – phân khúc chiếm tỷ trọng lớn nhất – nhu cầu du lịch tăng khoảng 15%. Các gia đình thường ưu tiên lựa chọn những tour trọn gói kéo dài từ ba đến năm ngày. Đây là phương án tối ưu nhất để đảm bảo sự thuận tiện trong việc di chuyển cùng trẻ nhỏ, đồng thời giúp kiểm soát chi phí hiệu quả cho cả nhà. Những chuyến đi này không chỉ là dịp để gia đình sum vầy, gắn kết tình cảm mà còn là khoảng thời gian quý giá để mọi người cùng nhau tận hưởng những trải nghiệm văn hóa mới mẻ tại các điểm đến.

Trong khi đó, các nhóm khách khác như công sở, người trẻ hay khách quốc tế cũng có những xu hướng lựa chọn tour riêng biệt với mức tăng trưởng từ 12% đến 22%.

Việc lựa chọn các gói tour trọn gói, phù hợp với nhịp sống gia đình truyền thống, sẽ giúp bạn có một hành trình khám phá đầy ý nghĩa, nơi mỗi điểm đến đều trở thành một kỷ niệm đẹp, nuôi dưỡng tâm hồn và làm phong phú thêm vốn sống của bản thân cũng như những người thân yêu.
```

### Person B — Ly thân, occupation không chuyên biệt (tránh Topic 'kinh doanh' lấn át marital_status)
```
Thị trường du lịch hè năm nay đang có sự phân hóa rõ rệt theo từng nhóm khách hàng. Trong đó, nhóm khách đi du lịch một mình đang tăng trưởng mạnh nhất với mức 22%. Đây là phân khúc dành cho những người trưởng thành, đã ly hôn hoặc đang tìm lại sự cân bằng cá nhân sau những biến cố cuộc sống. Thay vì các tour trọn gói cố định, nhóm này ưu tiên những hành trình linh hoạt, tự do, tập trung vào các trải nghiệm "du lịch chữa lành" tại những không gian yên tĩnh để khám phá văn hóa địa phương.

Các nhóm khách khác như công sở, gia đình, sinh viên và khách quốc tế cũng có nhu cầu du lịch tăng trưởng nhưng với mục đích và hình thức khác biệt, chủ yếu tập trung vào nghỉ dưỡng hoặc đi theo nhóm bạn.

Với tâm hồn ưa khám phá những di tích lịch sử và văn hóa, anh có thể tìm thấy sự đồng điệu trong những chuyến đi đơn lẻ, nơi mỗi địa danh như một trang sử cũ đang chờ được lật mở, giúp tâm trí tìm lại khoảng lặng bình yên giữa nhịp sống thường nhật. Những hành trình này không chỉ là sự dịch chuyển, mà còn là cơ hội để anh tự mình chạm vào những giá trị truyền thống, bồi đắp thêm vốn sống và sự tĩnh tại cho bản thân sau những ngày làm việc kỹ thuật bận rộn.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A tập trung rõ rệt vào sự tiện lợi cho gia đình và trẻ nhỏ, phù hợp với hồ sơ của Hoa. Bản tóm tắt B nhấn mạnh vào trải nghiệm cá nhân, sự tự do và du lịch chữa lành, phản ánh đúng nhu cầu của người đang tìm lại sự cân bằng sau ly thân. Sự phân hóa nội dung giữa hai bản tóm tắt hoàn toàn khớp với kỳ vọng về cá nhân hóa theo tình trạng hôn nhân.


---
## CQ8: Kỹ năng hiện có của người dùng có tác động loại bỏ phần hướng dẫn cơ bản (nhập môn) trong tóm tắt không?
**Trường kiểm tra:** skills_and_expertise (HARD)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Anh Dũng (thiết kế chuyên sâu) lược bỏ phần hướng dẫn cơ bản (mở phần mềm, công cụ cơ bản), chỉ giữ phần nâng cao (typography, motion design); tóm tắt cho Lê Văn Dung có thể giữ lại nhiều hơn hoặc trình bày khác do không có nền tảng thiết kế.

### Person A — Anh Dũng - Freelance designer nhiều năm kinh nghiệm
```
Năm 2025, xu hướng UX/UI tập trung vào việc tích hợp AI để phân tích hành vi và tối ưu hóa bố cục tự động, cùng với sự phát triển của chatbot xử lý ngôn ngữ tự nhiên.

Đối với các dự án chuyên sâu, trọng tâm kỹ thuật nằm ở typography động, cho phép biến thể font theo ngữ cảnh để truyền tải cảm xúc. Motion design được nâng cấp thông qua các micro-interactions có chủ đích, sử dụng chính xác easing curve và timing để tạo phản hồi tự nhiên. Các studio hiện đang đẩy mạnh việc đồng bộ hóa design system với animation token nhằm duy trì tính nhất quán khi mở rộng quy mô sản phẩm.

Giai đoạn này đánh dấu sự phân hóa rõ rệt giữa việc phổ cập công cụ thiết kế cơ bản và yêu cầu khắt khe về chiều sâu kỹ thuật cho các designer chuyên nghiệp.
```

### Person B — Lê Văn Dung - Công nhân, kỹ năng cơ bản
```
Năm 2025, xu hướng thiết kế giao diện (UX/UI) tập trung mạnh vào việc ứng dụng trí tuệ nhân tạo (AI) để tự động hóa và cá nhân hóa trải nghiệm người dùng.

Đối với người mới bắt đầu, việc làm quen với các công cụ thiết kế là bước nền tảng. Bạn cần nắm vững cách tạo file, sử dụng thanh công cụ, vẽ khung wireframe và ghi nhớ các phím tắt. Sau khi thành thạo giao diện, hãy tập trung thực hành dựng các bố cục cơ bản gồm phần đầu trang (header), nội dung chính và phần chân trang (footer).

Về mặt kỹ thuật, AI đóng vai trò quan trọng trong việc phân tích hành vi để tự động tối ưu hóa bố cục và hỗ trợ các tính năng như chatbot xử lý ngôn ngữ tự nhiên. Trong khi đó, các nhà thiết kế chuyên nghiệp đang đẩy mạnh việc sử dụng typography động và các chuyển động vi mô (micro-interactions) để tăng tính tương tác tự nhiên cho sản phẩm. Các xu hướng thiết kế hiện đại khác chỉ mang tính chất bổ trợ cho sự phát triển chung của ngành.

Tóm lại, đây là thời điểm công nghệ thiết kế trở nên thông minh hơn, đòi hỏi người làm nghề phải kết hợp giữa việc sử dụng thành thạo công cụ cơ bản và cập nhật các tính năng tự động hóa từ AI.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A đã lược bỏ hoàn toàn các hướng dẫn nhập môn (cách tạo file, phím tắt, bố cục cơ bản) và tập trung vào các kỹ thuật chuyên sâu như typography động và motion design, phù hợp với profile của Anh Dũng. Ngược lại, bản tóm tắt B giữ lại các hướng dẫn cơ bản dành cho người mới bắt đầu, phản ánh đúng sự khác biệt về trình độ người dùng theo kỳ vọng.


---
## CQ9: Vùng địa lý cư trú có làm tăng mức độ ưu tiên của nội dung địa phương trong tóm tắt không?
**Trường kiểm tra:** region (GENERAL)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho person A (Cần Thơ) giữ lại phần ĐBSCL/canh tác thông minh chống xâm nhập mặn rõ rệt hơn; tóm tắt cho person B (Hải Phòng) giữ lại phần nông nghiệp đô thị công nghệ cao ở ĐBSH rõ rệt hơn, cả hai đều lược bớt phần miền Trung/Tây Nguyên (không liên quan trực tiếp đến region của cả 2 person).

### Person A — Cô (Cần Thơ) - Buôn bán, gắn với chợ nổi miền Tây
```
Ngành nông nghiệp Việt Nam đang chuyển mình mạnh mẽ để thích ứng với biến đổi khí hậu, trong đó khu vực Đồng bằng sông Cửu Long (ĐBSCL) – nơi bạn đang sinh sống và kinh doanh – là tâm điểm chịu ảnh hưởng nặng nề nhất.

Tại ĐBSCL, tình trạng xâm nhập mặn đã trở thành quy luật hàng năm. Để duy trì hoạt động sản xuất và kinh doanh, người nông dân đang chuyển đổi từ tư duy "chống chọi" sang "thuận thiên". Các mô hình canh tác hiệu quả bao gồm:
- Chuyển đổi cơ cấu cây trồng: Thay vì độc canh lúa, các hợp tác xã áp dụng mô hình "con tôm ôm cây lúa" hoặc luân canh lúa - màu. Trong mùa mặn (tháng 2 đến tháng 4), nông dân nuôi tôm thẻ chân trắng, tôm sú; khi mùa mưa đến, họ chuyển sang trồng các giống lúa chịu mặn cao.
- Ứng dụng công nghệ: Việc sử dụng trạm đo độ mặn tự động kết nối qua điện thoại giúp nhà vườn chủ động thời điểm đóng mở cống ngăn mặn, bảo vệ hiệu quả các vùng cây ăn trái đặc sản.

Các vùng miền khác như Đồng bằng sông Hồng đang phát triển nông nghiệp công nghệ cao trong nhà màng, còn miền Trung và Tây Nguyên tập trung vào mô hình nông nghiệp tuần hoàn và tưới tiết kiệm để chống hạn.

Sự chuyển dịch này nhằm xây dựng nền nông nghiệp bền vững, tận dụng lợi thế tự nhiên và đặc thù kinh tế của từng vùng.
```

### Person B — Oanh - Hải Phòng, vùng đồng bằng sông Hồng
```
Ngành nông nghiệp Việt Nam đang thực hiện chuyển dịch chiến lược nhằm thích ứng với biến đổi khí hậu thông qua ba mô hình đặc thù theo vùng miền.

Tại Hải Phòng và các đô thị lớn thuộc Đồng bằng sông Hồng, nông nghiệp đang chuyển hướng mạnh mẽ sang mô hình công nghệ cao để tối ưu hóa quỹ đất hạn hẹp. Các hệ thống nhà màng, nhà kính tích hợp thủy canh và khí canh đa tầng được triển khai sát các khu công nghiệp, cho phép kiểm soát hoàn toàn quy trình sản xuất thông qua lập trình máy tính (tự động hóa châm phân, điều chỉnh độ ẩm, ánh sáng và nhiệt độ). Phương thức này giúp sản xuất rau và hoa cao cấp quanh năm, đạt năng suất gấp 4 đến 5 lần so với canh tác truyền thống, đồng thời thiết lập chuỗi cung ứng thực phẩm an toàn trực tiếp cho cư dân đô thị.

Các vùng miền khác cũng đang áp dụng những giải pháp thích ứng riêng biệt: Đồng bằng sông Cửu Long chuyển đổi sang canh tác thuận thiên (luân canh tôm - lúa, sử dụng giống chịu mặn), trong khi miền Trung và Tây Nguyên tập trung vào nông nghiệp tuần hoàn và công nghệ tưới tiết kiệm để chống hạn hán.

Sự chuyển đổi này không chỉ là giải pháp kỹ thuật mà còn là bước đi chiến lược nhằm xây dựng nền nông nghiệp bền vững, tận dụng tối đa lợi thế tự nhiên và đặc thù kinh tế của từng địa phương.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Hệ thống đã cá nhân hóa thành công nội dung: bản A tập trung sâu vào kỹ thuật canh tác tại ĐBSCL phù hợp với người dùng Cần Thơ, bản B tập trung vào nông nghiệp công nghệ cao tại ĐBSH phù hợp với người dùng Hải Phòng. Cả hai bản tóm tắt đều thực hiện tốt việc lược bớt thông tin về các vùng không liên quan (miền Trung/Tây Nguyên) bằng cách chỉ nhắc đến ngắn gọn trong một câu, đáp ứng đúng kỳ vọng về sự ưu tiên nội dung địa phương.


---
## CQ10: Phong cách du lịch (travel_persona) có làm thay đổi phần nào của văn bản du lịch được giữ lại trong tóm tắt không?
**Trường kiểm tra:** travel_persona (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Hiếu giữ lại rõ rệt phần nội dung thiên nhiên/sinh thái (Bạch Mã, thác Đỗ Quyên); tóm tắt cho Hà giữ lại rõ rệt phần nội dung di tích lịch sử/văn hóa (Đại Nội, chùa Thiên Mụ).

### Person A — Dương Xuân Hiếu - thích khám phá thiên nhiên, Vườn quốc gia Cát Tiên
```
Hành trình khám phá Vườn quốc gia Bạch Mã là điểm nhấn chính, phù hợp với định hướng du lịch thiên nhiên và sinh thái. Từ trung tâm, quãng đường hơn 40 km dẫn lên độ cao 1.450 m, nơi hệ sinh thái rừng nguyên sinh được bảo tồn nghiêm ngặt với các loài động thực vật quý hiếm, khí hậu mát mẻ và địa hình suối thác đặc trưng như thác Đỗ Quyên. Đây là môi trường lý tưởng để quan sát sự đa dạng sinh học và cảm nhận không gian rừng nguyên sinh.

Bên cạnh đó, hành trình cũng bao gồm việc tham quan các di tích lịch sử tại cố đô Huế như Đại Nội và chùa Thiên Mụ, cùng trải nghiệm ẩm thực địa phương.
```

### Person B — Ngô Thị Hà - thích điểm đến có giá trị lịch sử, văn hóa
```
Hành trình khám phá Huế là sự giao thoa tuyệt vời giữa thiên nhiên nguyên sơ và chiều sâu di sản, nơi mỗi bước chân đều mang lại những cảm xúc lắng đọng.

Buổi chiều tại cố đô là điểm nhấn đặc biệt, đưa ta trở về với không gian uy nghi của Đại Nội bên dòng sông Hương hiền hòa. Những cổng thành rêu phong, mái ngói lưu ly cùng tiếng chuông chùa Thiên Mụ ngân vang trên đồi Hà Khê như đưa thời gian lắng đọng, gợi lên vẻ đẹp cổ kính, thanh tịnh đầy hoài niệm. Khi hoàng hôn buông xuống, ánh nắng nhạt phủ lên mặt sông tạo nên một bức tranh yên bình, đậm chất văn hóa truyền thống mà bất cứ ai yêu lịch sử cũng đều trân quý.

Khép lại một ngày, hương vị đậm đà của bún bò Huế, cơm hến hay những đĩa bánh bèo nóng hổi từ các quán nhỏ ven đường mang đến sự ấm áp, gần gũi. Việc lựa chọn lưu trú dọc bờ nam sông Hương hoặc gần khu vực Đại Nội giúp hành trình khám phá các di tích trở nên thuận tiện và trọn vẹn hơn.

Bên cạnh đó, chuyến đi còn có những trải nghiệm ngắn tại Vườn quốc gia Bạch Mã với khí hậu mát mẻ và hệ sinh thái rừng nguyên sinh phong phú.

Huế không chỉ là một điểm đến, mà là nơi thiên nhiên và lịch sử song hành, tạo nên một sức hấp dẫn riêng biệt, để lại trong lòng người lữ khách những dư vị khó quên về một vùng đất giàu bản sắc.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A tập trung chi tiết vào Vườn quốc gia Bạch Mã và các đặc điểm sinh thái, đúng với sở thích của Hiếu. Bản tóm tắt B dành phần lớn dung lượng để mô tả không gian lịch sử, văn hóa tại Đại Nội và chùa Thiên Mụ, phản ánh đúng sở thích của Hà. Sự phân bổ nội dung giữa hai bản tóm tắt hoàn toàn khớp với kỳ vọng về cá nhân hóa.


---
## CQ11: Người dùng có nghề nghiệp sáng tạo thì bản tóm tắt về văn hóa nghệ thuật có cần giữ lại phần kỹ thuật chuyên môn không?
**Trường kiểm tra:** occupation/professional_persona (HARD) x arts_persona (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Anh Dũng giữ lại phần phân tích kỹ thuật (lớp màu, phối màu, trường phái); tóm tắt cho Lê Văn Dung chỉ giữ phần giới thiệu sự kiện và cảm nhận tổng thể.

### Person A — Anh Dũng - Freelance designer (nghề sáng tạo)
```
Triển lãm "Sắc màu và Ký ức" tại Bảo tàng Mỹ thuật Việt Nam đang là điểm hẹn nghệ thuật đầy cảm hứng, quy tụ 82 tác phẩm của 27 họa sĩ. Với tư cách là một designer, bạn sẽ đặc biệt quan tâm đến cách bố trí không gian trưng bày theo chủ đề, tạo mạch cảm xúc xuyên suốt từ những gam màu tươi sáng, chuyển động mạnh mẽ của nhịp sống đô thị đến những mảng màu trầm lắng, hoài niệm của phong cảnh làng quê.

Sự kiện là sự kết hợp tinh tế giữa các nghệ sĩ gạo cội và những gương mặt trẻ, mang đến cái nhìn đa chiều về cuộc sống đương đại. Các tác phẩm không chỉ dừng lại ở việc phác thảo hình ảnh mà còn là những câu chuyện về ký ức, khuyến khích người xem quan sát sâu hơn những điều bình dị. Đối với giới chuyên môn, đây là cơ hội quý giá để tiếp cận đa dạng phong cách thể hiện, từ bố cục, phối màu cho đến kỹ thuật xử lý chất liệu trên tranh.

Bên cạnh đó, triển lãm còn thu hút nhiều đối tượng khách tham quan khác như du khách quốc tế quan tâm đến văn hóa truyền thống hay các gia đình nhỏ. Trong ba tuần diễn ra, ban tổ chức sẽ triển khai các buổi giao lưu và chương trình hướng dẫn, tạo không gian kết nối cởi mở giữa họa sĩ và công chúng. Đây thực sự là một điểm đến lý tưởng để bạn tìm kiếm cảm hứng sáng tạo cho các dự án thiết kế và trang web của mình.
```

### Person B — Lê Văn Dung - Công nhân/lao động phổ thông
```
Triển lãm hội họa "Sắc màu và Ký ức" tại Bảo tàng Mỹ thuật Việt Nam đang là điểm hẹn văn hóa đầy cảm xúc, nơi 82 tác phẩm của 27 họa sĩ cùng hội tụ để kể những câu chuyện về đời sống thường nhật. Không gian triển lãm được sắp xếp khéo léo, dẫn dắt người xem đi từ những gam màu tươi sáng của nhịp sống đô thị hối hả đến những khoảng lặng hoài niệm của làng quê yên bình.

Với tâm hồn trân trọng những giá trị truyền thống, tôi thấy triển lãm như một bức tranh đa sắc về bản sắc Việt. Những tác phẩm khắc họa cảnh sinh hoạt, chợ truyền thống hay những góc phố thân quen không chỉ là nghệ thuật, mà còn là những mảnh ký ức được đánh thức, gợi nhắc về những điều bình dị mà đôi khi giữa guồng quay công việc, ta vô tình lãng quên. Sự kết hợp giữa các họa sĩ gạo cội và những gương mặt trẻ tạo nên một dòng chảy cảm xúc liền mạch, giúp người xem dễ dàng tìm thấy sự đồng điệu trong trải nghiệm cá nhân.

Triển lãm còn có các hoạt động giao lưu và chương trình hướng dẫn, mở ra cơ hội để những người yêu nghệ thuật như tôi có thể tiếp cận gần hơn với thế giới hội họa. Đây thực sự là một không gian đáng để dành thời gian ghé thăm, để lắng lại và cảm nhận vẻ đẹp của cuộc sống qua những nét vẽ đầy tâm huyết. Các chủ đề về phong cảnh miền núi hay trải nghiệm của du khách quốc tế cũng được lồng ghép tinh tế trong không gian trưng bày.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A cho Anh Dũng đã chủ động đề cập đến các yếu tố chuyên môn như 'bố cục', 'phối màu', 'kỹ thuật xử lý chất liệu' và gợi ý ứng dụng cho công việc thiết kế. Ngược lại, bản tóm tắt B cho Lê Văn Dung tập trung hoàn toàn vào cảm xúc, trải nghiệm cá nhân và ý nghĩa văn hóa, hoàn toàn lược bỏ các thuật ngữ kỹ thuật chuyên sâu, khớp chính xác với kỳ vọng đã đề ra.


---
## CQ12: Mức độ tham gia thể thao có quyết định phần nào của văn bản sức khỏe được ưu tiên trong tóm tắt không?
**Trường kiểm tra:** sports_persona (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Phương Chi có thể giữ phần dinh dưỡng thể thao/phục hồi cơ chuyên sâu hơn; tóm tắt cho Bà Nga giữ phần khuyến nghị sức khỏe cơ bản, vận động nhẹ.

### Person A — Phương Chi - năng động, tập bóng bàn/đi bộ thường xuyên
```
Giai đoạn 40–60 tuổi là thời điểm then chốt để tầm soát bệnh mạn tính và điều chỉnh lối sống nhằm giảm thiểu biến chứng. Việc quản lý sức khỏe cần tiếp cận đa chuyên khoa thay vì đơn lẻ, kết hợp khám định kỳ, dinh dưỡng và vận động.

Đối với nữ giới trung niên, nguy cơ tim mạch tăng đáng kể sau mãn kinh do thay đổi nội tiết; cần kiểm soát huyết áp, cholesterol, đường huyết và duy trì vận động tối thiểu 150 phút/tuần. Về xương khớp, tình trạng loãng xương và thoái hóa khớp đặc biệt phổ biến ở phụ nữ sau mãn kinh, đòi hỏi bổ sung canxi, vitamin D và thực hiện các bài tập chịu trọng lượng để duy trì khối cơ. Trong tầm soát ung bướu, cần tuân thủ lịch trình dựa trên độ tuổi và tiền sử cá nhân, đặc biệt lưu ý ung thư vú. Đối với các bệnh chuyển hóa như đái tháo đường típ 2 và gan nhiễm mỡ, tỷ lệ ở nữ giới tăng dần sau tuổi trung niên, do đó cần duy trì chế độ ăn cân đối, hạn chế thực phẩm chế biến sẵn, kiểm soát cân nặng và tái khám định kỳ.

Các vấn đề sức khỏe liên quan đến nam giới chỉ chiếm tỷ lệ nhỏ và không phải là ưu tiên trong lộ trình chăm sóc sức khỏe của nữ giới.
```

### Person B — Bà Nga - chỉ tập nhẹ nhàng, dưỡng sinh
```
Các bác sĩ khuyên người lớn tuổi cần chú ý chăm sóc sức khỏe để sống vui khỏe, độc lập.

Về tim mạch, phụ nữ sau mãn kinh có nguy cơ cao hơn, nên cần kiểm tra huyết áp và đường huyết thường xuyên. Việc vận động nhẹ nhàng hàng tuần rất tốt cho sức khỏe.

Về xương khớp, tình trạng loãng xương và thoái hóa khớp rất phổ biến ở người lớn tuổi. Bà cần chú ý bổ sung canxi và vitamin D để xương chắc khỏe, giúp việc đi lại và vận động hàng ngày được dễ dàng hơn.

Về tầm soát bệnh, dù là nam hay nữ, bà nên đi khám định kỳ theo lịch để phát hiện sớm các bệnh nguy hiểm.

Về chuyển hóa, để tránh bệnh tiểu đường và mỡ máu, bà nên ăn uống điều độ, hạn chế đồ ngọt và thực phẩm chế biến sẵn. Việc ngủ đủ giấc và kiểm tra sức khỏe thường xuyên là cách tốt nhất để phòng ngừa biến chứng.

Các vấn đề về sức khỏe ở những vùng miền khác hoặc các nhóm đối tượng khác không được đề cập chi tiết tại đây.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A cho Phương Chi tập trung vào các thuật ngữ chuyên sâu như 'bài tập chịu trọng lượng', 'duy trì khối cơ' và '150 phút/tuần', phù hợp với người năng động. Bản tóm tắt B cho Bà Nga sử dụng ngôn ngữ đơn giản, nhấn mạnh vào 'vận động nhẹ nhàng' và 'đi lại dễ dàng', phản ánh đúng sự khác biệt về mức độ ưu tiên theo hồ sơ người dùng.


---
## CQ13: Giới tính có làm thay đổi góc độ ưu tiên trong tóm tắt khi văn bản đề cập đến nhiều nhóm đối tượng không?
**Trường kiểm tra:** sex

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Hải giữ lại phần khuyến nghị dành cho nam giới (tim mạch, tuyến tiền liệt); tóm tắt cho Linh giữ lại phần dành cho nữ giới (xương khớp, tầm soát ung thư vú).

### Person A — Trần Văn Hải - Nam, 48 tuổi
```
Ở tuổi 48, anh cần chú trọng các kiểm tra y tế định kỳ để đảm bảo sức khỏe cho bản thân và gia đình. Đối với nam giới, bác sĩ khuyến cáo nên tầm soát tim mạch thường xuyên, bao gồm đo huyết áp, kiểm tra mỡ máu và làm điện tâm đồ. Đặc biệt, anh cần thực hiện xét nghiệm PSA mỗi 1-2 năm để kiểm tra tuyến tiền liệt, vì đây là bệnh lý có nguy cơ cao ở nam giới trên 45 tuổi. Ngoài ra, anh nên duy trì khám sức khỏe tổng quát hàng năm, thực hiện chế độ ăn uống lành mạnh, hạn chế muối, đường và tránh lạm dụng rượu bia, thuốc lá. Các khuyến nghị sức khỏe dành cho nữ giới ở độ tuổi này không áp dụng cho anh.
```

### Person B — Chị Linh - Nữ, 45 tuổi
```
Ở tuổi 45, chị cần đặc biệt chú ý đến sức khỏe xương khớp do mật độ xương giảm nhanh sau giai đoạn tiền mãn kinh. Chị nên bổ sung canxi và vitamin D, đồng thời thực hiện chụp nhũ ảnh định kỳ mỗi 1-2 năm để tầm soát ung thư vú.

Bên cạnh đó, chị cần duy trì khám sức khỏe tổng quát mỗi năm một lần, thực hiện chế độ ăn cân bằng, hạn chế muối, đường và tránh sử dụng rượu bia quá mức. Đối với nam giới, các bác sĩ khuyến cáo tầm soát tim mạch và tuyến tiền liệt định kỳ để phát hiện sớm các bệnh lý liên quan.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A tập trung vào các khuyến nghị sức khỏe nam giới (tim mạch, tuyến tiền liệt) cho anh Hải, trong khi bản B ưu tiên các vấn đề sức khỏe nữ giới (xương khớp, ung thư vú) cho chị Linh. Sự khác biệt này hoàn toàn khớp với expected_effect, mặc dù bản B có đề cập thêm thông tin nam giới ở cuối nhưng vẫn giữ được trọng tâm ưu tiên cho nữ giới.


---
## CQ14: Quốc gia cư trú (cố định Việt Nam) có đóng vai trò ràng buộc cứng loại bỏ/chú thích nội dung không phù hợp ngữ cảnh Việt Nam trong tóm tắt không?
**Trường kiểm tra:** country (HARD, cố định)

**Loại test:** single_constraint

**Kỳ vọng (expected_effect):** Bản tóm tắt không trình bày chính sách thuế EU hoặc luật California như thể áp dụng trực tiếp cho người đọc tại Việt Nam; nội dung nước ngoài bị lược bỏ hoặc được chú thích rõ là không áp dụng trực tiếp.

### Person A — Trần Thùy Thảo - dùng làm đại diện chung
```
Các doanh nghiệp xuất khẩu Việt Nam đang phải chuẩn bị thích ứng với Cơ chế điều chỉnh biên giới carbon (CBAM) của Liên minh châu Âu (EU). Lưu ý rằng các quy định này của EU không áp dụng trực tiếp tại Việt Nam mà chỉ ảnh hưởng gián tiếp đến hoạt động thương mại quốc tế và chuỗi cung ứng.

Đối với các doanh nghiệp, đặc biệt trong lĩnh vực sản xuất và chế biến, việc đáp ứng yêu cầu về phát thải, truy xuất dữ liệu và minh bạch chuỗi cung ứng đã trở thành tiêu chuẩn thương mại bắt buộc. Các đơn vị cần tập trung vào việc chuẩn hóa dữ liệu, nâng cấp quy trình sản xuất và xây dựng hệ thống quản trị phát thải để duy trì năng lực cạnh tranh.

Thách thức lớn nhất hiện nay là năng lực quản lý dữ liệu và sự phối hợp giữa các bộ phận trong quy trình sản xuất, thay vì chỉ là đầu tư thiết bị. Đối với các doanh nghiệp vừa và nhỏ, chi phí xây dựng hệ thống đo lường và kiểm định độc lập là một rào cản đáng kể. Tuy nhiên, đây cũng là cơ hội để cải thiện hiệu quả sử dụng năng lượng, giảm chi phí vận hành và nâng cao uy tín trên thị trường. Các hiệp hội ngành hàng hiện đang hỗ trợ doanh nghiệp thông qua các chương trình đào tạo và hướng dẫn kỹ thuật để cập nhật yêu cầu mới. Các xu hướng phát triển bền vững tại các thị trường khác chỉ mang tính tham khảo.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt đã thực hiện tốt việc chú thích rõ ràng rằng các quy định CBAM của EU không áp dụng trực tiếp tại Việt Nam mà chỉ có ảnh hưởng gián tiếp. Đồng thời, văn bản cũng khẳng định các xu hướng phát triển bền vững tại thị trường khác chỉ mang tính tham khảo, đáp ứng hoàn hảo kỳ vọng về việc phân định ngữ cảnh địa lý cho người đọc tại Việt Nam.


---
## CQ15: Giá trị sống và thế giới quan (persona) có ảnh hưởng đến văn phong và ngữ điệu của bản tóm tắt không?
**Trường kiểm tra:** persona (GENERAL)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Hương súc tích, thiên về số liệu/kết luận rõ ràng; tóm tắt cho Bà Nga có thể nhẹ nhàng, gần gũi đời thường hơn.

### Person A — Đỗ Thanh Hương - quản lý, thực dụng, tham vọng
```
Kết quả khảo sát quý II trên 2.400 người lao động cho thấy bức tranh việc làm đang ổn định, nhưng áp lực về thu nhập và chi phí sinh hoạt vẫn là mối quan tâm hàng đầu. Tại TP. Hồ Chí Minh, 61% người lao động hài lòng với công việc hiện tại, 27% chưa hài lòng nhưng chưa có kế hoạch nghỉ việc, và 12% đang chủ động tìm kiếm cơ hội mới. Đáng chú ý, 68% nhận định chi phí sinh hoạt tăng nhanh hơn thu nhập, 54% thường xuyên làm thêm giờ. Các khu vực khác như Hà Nội, Đà Nẵng, Cần Thơ và các tỉnh công nghiệp cũng ghi nhận những xu hướng tương tự về áp lực tài chính và cân bằng công việc.

Về kỳ vọng môi trường làm việc, 72% người lao động ưu tiên cơ hội học hỏi và phát triển kỹ năng, vượt qua tiêu chí phúc lợi (69%). Ngoài ra, 58% mong muốn làm việc linh hoạt và 64% đề cao các chính sách hỗ trợ sức khỏe tinh thần.

Đối với các trường hợp cụ thể, chị Hương (lĩnh vực thương mại điện tử) cho thấy mô hình làm việc kết hợp văn phòng và từ xa giúp tối ưu hóa sự cân bằng giữa công việc và cuộc sống cá nhân. Các trường hợp khác tại Hà Nội, Bình Dương ghi nhận những thách thức riêng về thu nhập và định hướng nghề nghiệp.

Tổng kết, người lao động hiện nay đặt trọng tâm vào cơ hội phát triển nghề nghiệp, sự linh hoạt trong cách thức vận hành và chất lượng môi trường làm việc, coi đây là các tiêu chí then chốt để quyết định gắn bó lâu dài với doanh nghiệp.
```

### Person B — Bà Nga - tận hưởng tuổi già, bình yên
```
Khảo sát mới đây trên 2.400 người lao động tại nhiều tỉnh thành, trong đó có Đà Nẵng, cho thấy tình hình việc làm đang dần ổn định. Tuy nhiên, đa số người lao động vẫn lo lắng vì chi phí sinh hoạt tăng nhanh hơn thu nhập.

Người lao động hiện nay không chỉ quan tâm đến tiền lương mà còn chú trọng đến cơ hội học hỏi kỹ năng, môi trường làm việc và sức khỏe tinh thần. Các xu hướng làm việc tại Hà Nội, TP. Hồ Chí Minh và các tỉnh công nghiệp khác cũng được ghi nhận nhưng không đáng kể so với thực tế tại địa phương.

Đối với việc quản lý chi tiêu gia đình, kết quả cho thấy nhiều người đang phải tìm thêm nguồn thu nhập để đảm bảo cuộc sống ổn định trước những biến động của thị trường. Nhìn chung, sự cân bằng giữa thu nhập và chi phí sinh hoạt vẫn là mối quan tâm hàng đầu của mọi người.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A thể hiện rõ tư duy quản lý với số liệu chi tiết và cấu trúc logic, phù hợp với persona thực dụng. Bản tóm tắt B lược bỏ các con số khô khan, tập trung vào khía cạnh đời thường và cảm xúc, phản ánh đúng phong cách nhẹ nhàng, gần gũi của bà Nga.


---
## CQ16: Nền tảng văn hóa có làm thay đổi mức độ cộng hưởng của người dùng với cùng một văn bản không?
**Trường kiểm tra:** cultural_background (GENERAL)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Bà Nga nhấn vào phong tục truyền thống (thắp hương, gói bánh chưng, đi chùa); tóm tắt cho Hiếu có thể giữ cả phần xu hướng hiện đại (du lịch nước ngoài, tiệc Tết hiện đại).

### Person A — Bà Nga - gắn bó văn hóa truyền thống Đà Nẵng (bài chòi, lễ hội)
```
Tết Nguyên Đán đang đến gần, không khí tại TP. Hồ Chí Minh rất nhộn nhịp với nhiều hoạt động mua sắm.

Đối với các gia đình giữ nếp sống truyền thống, việc chuẩn bị Tết vẫn đầy đủ các nghi lễ như dọn dẹp bàn thờ, bày mâm ngũ quả, gói bánh chưng, bánh tét cùng con cháu. Chiều 30 Tết thắp hương mời tổ tiên, sáng mùng Một đi chùa lễ Phật, sau đó là tục chúc Tết, mừng tuổi ông bà và lì xì cho trẻ nhỏ để giữ gìn văn hóa cội nguồn.

Một số người dân ở đô thị chọn cách đón Tết hiện đại hơn như đi du lịch nước ngoài hoặc đặt tiệc tại nhà hàng.

Sức mua sắm năm nay ổn định. Giao thông đang vào giai đoạn cao điểm khi mọi người bắt đầu về quê đón Tết.
```

### Person B — Dương Xuân Hiếu - sống chung cư hiện đại, pha trộn văn hóa
```
Dịp Tết Nguyên Đán tại TP.HCM ghi nhận sự nhộn nhịp tại các tuyến đường và trung tâm thương mại, với sức mua ổn định và lưu lượng giao thông cao điểm tại các bến xe, nhà ga, sân bay.

Đối với người dân tại các đô thị lớn, xu hướng đón Tết đang chuyển dịch mạnh mẽ sang phong cách hiện đại và linh hoạt. Thay vì các nghi lễ truyền thống, nhiều người ưu tiên đặt tour du lịch nước ngoài (Nhật Bản, Hàn Quốc, Thái Lan) để tận dụng kỳ nghỉ dài. Các hoạt động tổ chức tiệc Tết tại nhà hàng theo hình thức buffet, trang trí nhà cửa tối giản, hoặc sử dụng các ứng dụng giao hàng để đặt sẵn thực phẩm thay vì tự tay chuẩn bị đang trở nên phổ biến. Trong khi đó, một bộ phận nhỏ người dân vẫn duy trì các nghi lễ truyền thống như gói bánh, cúng tổ tiên và đi chùa lễ Phật.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A tập trung chi tiết vào các nghi lễ truyền thống như dọn bàn thờ, gói bánh, đi chùa, phù hợp với đối tượng Bà Nga. Bản tóm tắt B ưu tiên các xu hướng hiện đại như du lịch nước ngoài và dịch vụ tiện ích, phản ánh đúng sự khác biệt về phong cách sống của Hiếu theo kỳ vọng.


---
## CQ17: Khi trường HARD (zone, occupation) và trường SOFT (travel_persona) xung đột nhau, tóm tắt có ưu tiên theo HARD không?
**Trường kiểm tra:** zone + occupation (HARD) vs travel_persona (SOFT) - quan hệ uu_tien_hon

**Loại test:** single_constraint

**Kỳ vọng (expected_effect):** Tóm tắt giữ lại phần khám phá tự túc bằng xe máy, ẩm thực vỉa hè, chi phí hợp lý (phù hợp HARD: nông thôn, buôn bán) hơn là phần resort 5 sao/tour cao cấp (dù travel_persona SOFT có xu hướng quốc tế/cao cấp).

### Person A — Chị Mai - Nông Thôn/Buôn bán (HARD) nhưng travel_persona thích quốc tế (SOFT)
```
Hạ Long là lựa chọn lý tưởng cho chuyến đi ngắn ngày, chỉ cách Hà Nội hơn hai giờ di chuyển. Điểm đến này mang lại trải nghiệm thú vị khi kết hợp được hai không gian đối lập chỉ cách nhau cây cầu Bãi Cháy.

Với chị, Hòn Gai là nơi đáng để dừng chân nhất bởi những góc phố ẩm thực lâu đời, các công trình tâm linh và nhịp sống bình dị, chân chất của người dân vùng biển – tựa như hơi thở thân thuộc của quê hương Đà Nẵng. Ngược lại, Bãi Cháy là khu vực hiện đại với nhiều resort và khu vui chơi giải trí.

Hai khu vực này chỉ cách nhau khoảng 15 phút di chuyển, rất thuận tiện để chị tự lái xe hoặc đi taxi khám phá trọn vẹn trong 48 giờ. Đây là hành trình kết hợp hài hòa giữa nét truyền thống và sự sôi động, hứa hẹn mang lại những kỷ niệm đáng nhớ.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt đã ưu tiên tập trung vào trải nghiệm khám phá tự túc, ẩm thực bình dân và nhịp sống giản dị tại Hòn Gai, thay vì nhấn mạnh vào các resort cao cấp hay các yếu tố quốc tế. Nội dung này hoàn toàn phù hợp với đặc điểm HARD (nông thôn, buôn bán) của chị Mai, dù travel_persona có xu hướng ngược lại.


---
## CQ18: Sự kết hợp giữa nghề nghiệp và khu vực sống có tạo ra yêu cầu tóm tắt đặc thù không?
**Trường kiểm tra:** occupation x zone (HARD x SOFT combo)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Cùng nghề buôn bán nhưng tóm tắt cho Minh (nông thôn) giữ phần giá nông sản/kênh phân phối truyền thống; tóm tắt cho Thảo (đô thị) giữ phần thương mại điện tử/logistics.

### Person A — Minh - Buôn bán, Nông Thôn
```
Việc bán nông sản hiện nay đang có nhiều thay đổi, nhưng cách làm truyền thống vẫn rất quan trọng và phù hợp với người làm nghề như anh.

Tại các vùng nông thôn, việc tiêu thụ qua thương lái, hợp tác xã và chợ đầu mối vẫn là cách tốt nhất. Cách này giúp anh thu mua hàng ngay tại chỗ, giảm chi phí vận chuyển và không phải lo lắng về khâu bảo quản hay công nghệ phức tạp. Các hợp tác xã hiện nay cũng hỗ trợ rất tốt việc phân loại và đóng gói, giúp đầu ra ổn định hơn. Việc địa phương nâng cấp chợ đầu mối và trung tâm thu gom cũng giúp giá cả ổn định, tránh tình trạng được mùa mất giá.

Ở các thành phố lớn, người dân đang chuyển sang mua hàng qua mạng và ứng dụng điện thoại, đòi hỏi hệ thống kho bãi và vận chuyển phải hiện đại hơn. Tuy nhiên, việc bán hàng trực tuyến vẫn còn khó khăn với nhiều nông dân do thiếu kỹ năng công nghệ và hạ tầng chưa đồng bộ.

Hướng đi tốt nhất hiện nay là kết hợp cả hai: anh và các hợp tác xã vẫn giữ vai trò thu gom, sơ chế tại vùng sản xuất, còn các đơn vị vận chuyển và sàn thương mại điện tử sẽ lo khâu đưa hàng đến tay người mua ở thành phố. Sự kết hợp này giúp nông sản bán được giá hơn và mở rộng thị trường, giúp công việc kinh doanh của anh bền vững hơn.
```

### Person B — Phạm Thị Thảo - Buôn bán, Đô Thị
```
Hoạt động tiêu thụ nông sản hiện nay đang chuyển dịch theo mô hình kết hợp giữa kênh truyền thống và thương mại điện tử.

Tại các đô thị lớn như TP.HCM, hành vi tiêu dùng đã thay đổi rõ rệt khi khách hàng ưu tiên đặt mua nông sản qua các sàn thương mại điện tử và ứng dụng trực tuyến. Sự phát triển này đòi hỏi doanh nghiệp phải đầu tư mạnh vào hạ tầng logistics (kho lạnh, trung tâm phân phối, giao hàng nhanh) và áp dụng công nghệ truy xuất nguồn gốc bằng mã QR để đảm bảo chất lượng sản phẩm. Các nền tảng số hiện cung cấp công cụ phân tích nhu cầu thị trường, dự báo sức mua và quản lý đơn hàng theo thời gian thực, giúp tối ưu hóa lượng hàng tồn kho, giảm chi phí vận hành và nâng cao hiệu quả phân phối.

Tại các vùng sản xuất nông nghiệp, mạng lưới phân phối truyền thống thông qua thương lái và hợp tác xã vẫn đóng vai trò chủ chốt trong việc thu gom, sơ chế và tập trung nguồn hàng nhờ quy trình đơn giản, chi phí thấp. Các địa phương đang tiếp tục nâng cấp hệ thống chợ đầu mối và trung tâm thu gom để ổn định giá cả và hỗ trợ nông dân.

Việc kết hợp giữa hệ thống thu mua truyền thống tại vùng sản xuất và các nền tảng phân phối hiện đại tại đô thị là hướng đi tối ưu để nâng cao giá trị nông sản, mở rộng thị trường và tạo chuỗi cung ứng bền vững. Các chương trình hỗ trợ hiện nay đang tập trung đào tạo kỹ năng số và xây dựng thương hiệu cho nông sản để nông dân có thể tham gia hiệu quả hơn vào chuỗi giá trị này.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 0.95

- **Lý do:** Bản tóm tắt A tập trung sâu vào các kênh truyền thống (thương lái, hợp tác xã, chợ đầu mối) phù hợp với bối cảnh nông thôn của Minh. Bản tóm tắt B nhấn mạnh vào hạ tầng logistics, thương mại điện tử và công nghệ quản lý, phản ánh đúng nhu cầu của người làm buôn bán tại đô thị. Sự phân hóa trọng tâm nội dung giữa hai bản tóm tắt hoàn toàn khớp với kỳ vọng đã đề ra.


---
## CQ19: Mức độ tham gia nghệ thuật (arts_persona) có ảnh hưởng đến khả năng tiếp nhận văn phong giàu hình ảnh/ẩn dụ trong bản tóm tắt không?
**Trường kiểm tra:** arts_persona (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Oanh có thể dùng ngôn ngữ giàu hình ảnh/ẩn dụ hơn khi mô tả triển lãm; tóm tắt cho Dung trực tiếp, tường minh hơn.

### Person A — Oanh - đam mê hội họa, thường xuyên dự triển lãm (arts cao)
```
Triển lãm hội họa "Sắc màu và Ký ức" tại Bảo tàng Mỹ thuật Việt Nam hiện đang là điểm hẹn văn hóa đầy sức gợi, nơi 82 tác phẩm của 27 họa sĩ hội tụ, dệt nên một bức tranh đa diện về đời sống đương đại. Không gian trưng bày được phân bổ khoa học theo chủ đề, dẫn dắt người xem đi từ những gam màu tươi sáng, chuyển động của nhịp sống đô thị đến những khoảng lặng trầm mặc, hoài niệm của ký ức.

Đối với một người nghiên cứu như tôi, sự kết hợp giữa các nghệ sĩ gạo cội và những gương mặt trẻ tạo nên một cấu trúc triển lãm giàu tính đối thoại. Cách sắp xếp này không chỉ phản ánh sự tiếp nối thế hệ mà còn mở ra không gian để phân tích các phong cách biểu đạt khác nhau, từ những mảng màu nhẹ nhàng khắc họa phong cảnh miền núi đến bố cục rộng mở của phố thị. Triển lãm không áp đặt một thông điệp duy nhất, mà như họa sĩ Nguyễn Minh An chia sẻ, mỗi tác phẩm là một điểm chạm, khơi gợi những câu chuyện riêng biệt gắn liền với trải nghiệm cá nhân của mỗi người xem.

Sự kiện này thực sự là một lát cắt thực tế đầy giá trị, nơi những điều bình dị được nâng tầm thành nghệ thuật, khuyến khích chúng ta quan sát sâu hơn vào những chuyển động của đời sống thường nhật. Các hoạt động giao lưu giữa họa sĩ và công chúng, cùng chương trình hướng dẫn chuyên sâu, hứa hẹn sẽ là môi trường lý tưởng để những người yêu nghệ thuật tại Hải Phòng và các địa phương khác cùng thảo luận, chia sẻ góc nhìn chuyên môn. Các nhóm khách tham quan khác như gia đình hay du khách quốc tế cũng tìm thấy những trải nghiệm riêng biệt tại đây. Với thời gian kéo dài ba tuần, đây là cơ hội quý giá để tiếp cận các giá trị thẩm mỹ và văn hóa truyền thống được tái hiện qua lăng kính hội họa đương đại.
```

### Person B — Anh Tuấn - thợ xây dựng, ít quan tâm nghệ thuật (arts thấp, dùng ngôn ngữ dè dặt 'có thể thích')
```
Triển lãm hội họa "Sắc màu và Ký ức" đang diễn ra tại Bảo tàng Mỹ thuật Việt Nam ở Hà Nội. Đây là nơi trưng bày 82 tác phẩm của 27 họa sĩ, tập trung vào các chủ đề về đời sống, con người và cảnh vật.

Không gian triển lãm được sắp xếp ngăn nắp theo từng chủ đề, giúp người xem dễ dàng quan sát. Các bức tranh khắc họa nhịp sống đô thị, khung cảnh làng quê và đời sống thường nhật một cách gần gũi. Những tác phẩm này gợi lại nhiều ký ức và cảm xúc quen thuộc về cuộc sống, giúp người xem trân trọng hơn những điều bình dị xung quanh mình.

Triển lãm là nơi kết nối giữa các họa sĩ lâu năm và những gương mặt trẻ, tạo nên sự đa dạng trong cách thể hiện. Ngoài việc trưng bày, bảo tàng còn tổ chức các buổi giao lưu và chương trình hướng dẫn cho học sinh để mọi người thêm hiểu và yêu quý nghệ thuật. Các hoạt động nghệ thuật ở những vùng miền khác cũng được tổ chức tương tự để phục vụ công chúng. Đây là điểm đến phù hợp cho các gia đình muốn dành thời gian cuối tuần cùng nhau.
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt A sử dụng ngôn ngữ giàu hình ảnh và ẩn dụ (ví dụ: 'dệt nên một bức tranh đa diện', 'khoảng lặng trầm mặc', 'điểm chạm') phù hợp với người có chuyên môn nghệ thuật. Bản tóm tắt B sử dụng ngôn ngữ trực tiếp, tường minh và tập trung vào thông tin thực tế, phù hợp với người ít quan tâm đến nghệ thuật, phản ánh đúng kỳ vọng về sự cá nhân hóa văn phong.


---
## CQ20: Đam mê và sở thích cá nhân có làm tăng ngưỡng chấp nhận độ dài tóm tắt của người dùng trong chủ đề họ yêu thích không?
**Trường kiểm tra:** hobbies_and_interests (SOFT)

**Loại test:** pair_comparison

**Kỳ vọng (expected_effect):** Tóm tắt cho Phương Hạnh (B) có thể dài hơn, giữ lại nhiều chi tiết về công thức truyền thống cầu kỳ; tóm tắt cho Anh Thanh (A) ngắn gọn hơn, chỉ giữ phần công thức nhanh gọn cơ bản.

### Person A — Anh Thanh - sở thích đa dạng (lễ hội, cờ, làm vườn), không gắn bó sâu với ẩm thực
```
Việc giữ gìn hương vị truyền thống trong nấu ăn đang gặp thách thức trước xu hướng nấu nhanh, tiện lợi của nhịp sống hiện đại.

Với món bún bò Huế, các nghệ nhân khẳng định giá trị nằm ở sự tỉ mỉ: xương bò phải được làm sạch, ninh liên tục từ 8 đến 10 giờ, hớt bọt kỹ để nước dùng trong. Việc rang hành, gừng, sả đập dập và lọc mắm ruốc đúng giai đoạn là những kỹ thuật cốt lõi để tạo nên mùi thơm và vị ngọt tự nhiên. Việc tự làm sa tế từ ớt khô, dầu điều cũng giúp hương vị cân bằng hơn so với đồ làm sẵn. Những kỹ thuật này là kinh nghiệm quý báu cần được truyền lại để giữ gìn bản sắc.

Ngược lại, nhiều người trẻ hiện nay chọn cách nấu rút gọn bằng nồi áp suất, dùng gia vị tổng hợp hoặc nguyên liệu sơ chế sẵn để tiết kiệm thời gian, chấp nhận hương vị chỉ đạt khoảng 80-90% so với cách nấu truyền thống.

Tại các vùng miền khác, các xu hướng ẩm thực cũng đang có sự chuyển dịch tương tự giữa việc bảo tồn giá trị cũ và thích nghi với sự tiện lợi.

Các chuyên gia cho rằng cả hai cách nấu đều có chỗ đứng riêng. Việc chọn cách nào tùy thuộc vào quỹ thời gian và mục đích của mỗi người khi vào bếp.
```

### Person B — Phương Hạnh - đam mê ẩm thực Hải Phòng cụ thể, thường tự nấu ăn tại nhà
```
Ẩm thực Việt hiện nay đang chứng kiến sự song hành giữa hai xu hướng: giữ gìn hương vị truyền thống và tối ưu hóa thời gian chế biến.

Đối với những người yêu thích sự tỉ mỉ, cách nấu truyền thống như món bún bò Huế đòi hỏi sự kiên nhẫn tuyệt đối. Để có nồi nước dùng trong vắt, đậm đà vị ngọt tự nhiên, người nấu phải kỳ công ninh xương từ 8 đến 10 giờ, liên tục hớt bọt, rang hành gừng tạo mùi thơm và lọc mắm ruốc kỹ càng. Những kỹ thuật này không chỉ tạo nên linh hồn cho món ăn mà còn là di sản kinh nghiệm quý báu được truyền lại qua nhiều thế hệ, giúp giữ trọn vẹn màu sắc và hương vị đặc trưng.

Ngược lại, với nhịp sống đô thị bận rộn, nhiều người trẻ lựa chọn các phiên bản rút gọn để tự tay chuẩn bị bữa ăn tại nhà sau giờ làm việc. Thay vì dành cả ngày trong bếp, việc sử dụng nồi áp suất giúp rút ngắn thời gian ninh xương xuống chỉ còn khoảng một giờ. Các nguyên liệu sơ chế sẵn, thịt thái sẵn hay gia vị cô đặc cũng được ưu tiên để tạo ra những món ăn đạt khoảng 80-90% hương vị truyền thống, đáp ứng nhu cầu sinh hoạt hằng ngày một cách nhanh chóng và tiện lợi.

Tại các lễ hội ẩm thực, trong khi các nghệ nhân nhấn mạnh vào việc bảo tồn kỹ thuật nấu nướng, thì khu vực trải nghiệm nấu nhanh lại thu hút đông đảo các bạn trẻ tìm kiếm những mẹo nhỏ để tự chủ việc bếp núc. Các chuyên gia cho rằng hai xu hướng này không loại trừ nhau; việc lựa chọn cách nấu nào hoàn toàn phụ thuộc vào quỹ thời gian và mong muốn trải nghiệm của mỗi người.

*Lưu ý: Các nội dung về lễ hội ẩm thực tại miền Trung chỉ mang tính chất tham khảo ngắn gọn.*
```

### Đánh giá LLM judge
- **Verdict:** PASS

- **Confidence:** 1.0

- **Lý do:** Bản tóm tắt B dài hơn và tập trung sâu vào các chi tiết kỹ thuật nấu nướng truyền thống (như cách tạo linh hồn món ăn, di sản kinh nghiệm), trong khi bản A tập trung vào thông tin tổng quát và sự đối lập giữa hai xu hướng. Sự khác biệt này phản ánh đúng kỳ vọng về việc cá nhân hóa nội dung dựa trên mức độ đam mê ẩm thực của người dùng.
