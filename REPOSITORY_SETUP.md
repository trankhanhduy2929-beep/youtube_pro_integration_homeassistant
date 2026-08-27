# Đăng source lên GitHub

Gói source đã được chuẩn bị cho repository độc lập có tên đề xuất:

```text
youtube-pro-home-assistant
```

## Cách 1: Upload bằng giao diện GitHub

1. Tạo repository mới `youtube-pro-home-assistant`.
2. Giải nén gói source `youtube_pro_homeassistant_v5.1.0_source.zip` hoặc thư mục repository hiện tại.
3. Mở thư mục `youtube-pro-home-assistant` vừa giải nén.
4. Upload **toàn bộ nội dung bên trong**, bao gồm thư mục ẩn `.github`.
5. Commit vào nhánh `main`.
6. Kiểm tra tab **Actions**; workflow `Validate YouTube Pro Integration` phải xanh.

Để tạo Release tự động bằng giao diện GitHub, tạo tag/release `v5.1.0`. Nếu
GitHub không chạy workflow khi tạo release trực tiếp, dùng cách dòng lệnh bên
dưới để push tag.

## Cách 2: Dùng Git

```bash
git init
git add .
git commit -m "Release YouTube Pro integration 5.1.0"
git branch -M main
git remote add origin https://github.com/trankhanhduy2929-beep/youtube-pro-home-assistant.git
git push -u origin main
git tag v5.1.0
git push origin v5.1.0
```

Sau khi tag được push, workflow Release tạo các asset `youtube_pro.zip`,
`youtube_pro_manual.zip`, source ZIP và checksum.

## Thêm vào HACS

Trong HACS, thêm custom repository:

```text
https://github.com/trankhanhduy2929-beep/youtube-pro-home-assistant
```

Chọn category **Integration**. HACS sẽ tải asset `youtube_pro.zip` từ GitHub
Release vì `hacs.json` đã bật `zip_release` và khai báo đúng filename.
