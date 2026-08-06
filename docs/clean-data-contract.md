# Clean data contract

`build_clean_dataframe(records, run_date)` tạo dataset chuẩn dùng chung cho index,
evaluation, observability, corruption và repair.

## Quy tắc

- `paper_id`, `title`: bắt buộc; chuẩn hóa khoảng trắng; loại record nếu rỗng.
- `summary`, URL và `comment`: null được đổi thành chuỗi rỗng.
- Chuỗi từ Crossref được giải mã HTML entity (`&amp;` → `&`) và loại bỏ
  JATS/HTML markup trước khi tạo các trường dẫn xuất và embedding text.
- `authors`, `categories`: null thành list rỗng; bỏ phần tử rỗng và trùng
  không phân biệt hoa/thường; giữ thứ tự đầu tiên.
- `primary_category`: nếu có mà chưa nằm trong `categories`, thêm vào đầu list.
- `published`, `updated`: parse thành `datetime64[ns, UTC]`; giá trị sai thành
  `NaT` để quality check phát hiện, không tự bịa ngày.
- Trùng `paper_id`: giữ record có `updated` mới nhất; nếu hòa, giữ record xuất
  hiện sau trong input.
- `age_days`: số ngày từ ngày `published` đến `run_date`, kiểu nullable `Int64`;
  ngày tương lai nhận 0, thiếu/sai ngày nhận `NA`.

## Trường dẫn xuất

`paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`,
`published`, `updated`, `age_days`, `authors_joined`, `categories_joined`,
`summary_chars`, `text_for_embedding`, `abs_url`, `pdf_url`, `comment`.

`text_for_embedding` ghép các field có nhãn theo thứ tự:

```text
Title: <title>
Summary: <summary>             # bỏ dòng nếu rỗng
Authors: <authors_joined>      # bỏ dòng nếu rỗng
Categories: <categories_joined> # bỏ dòng nếu rỗng
```

## Sample validation CP1

```powershell
python -m unittest tests/test_cleaning.py -v
```

Ba test kiểm tra: schema và phép biến đổi raw → clean; xử lý null/ngày sai/trường
bắt buộc; deduplicate và `age_days`.

Tạo artifact CP1 từ `data/raw/crossref_records.json`:

```powershell
python script/run_cleaning_cp1.py
```

Đầu ra gồm `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` và
`data/clean/cleaning_report.json`. Report ghi tổng input/output cùng count record
bị loại do thiếu ID, thiếu title, trùng ID, ngày sai và summary rỗng.
