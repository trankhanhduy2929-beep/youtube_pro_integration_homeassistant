# Changelog

## 5.1.0 - 2026-08-27

- Đồng bộ custom integration với Add-on YouTube Pro 5.1.0.
- Media Browser truyền target player khi duyệt queue để hiển thị đúng danh sách tiếp theo của loa.
- Mở rộng `enqueue` với `entity_id` và `position: next|end`.
- Thêm service `start_radio` và API client tạo đài phát audio/video với `replace|append`.
- Giữ nguyên token riêng, auto-discovery, license boundary và các service cũ.

## 5.0.1 - 2026-08-26

- Đồng bộ custom integration với Add-on YouTube Pro 5.0.1.
- Thêm khu vực **Video YouTube** trong Media Browser, tìm kiếm video, thumbnail và resolve video relay.
- Truyền `media_kind` qua API integration; giữ mặc định audio để tương thích ngược.
- Truyền target `media_player` khi resolve video để add-on chọn đúng relay hoặc audio fallback cho HomePod/AirPlay.
- Tự dò endpoint add-on qua Supervisor/DNS nội bộ; không cần nhập IP Home Assistant trong cấu hình thông thường.
- Mở rộng service `play` và `enqueue` cho nội dung video.
- Giữ nguyên playlist, queue, history, timer, điều khiển playback và token riêng.

## 4.0.0 - 2026-08-25

- Tách custom integration YouTube Pro khỏi bản Lite.
- Thêm Media Browser native, tìm kiếm, playlist, queue, history và playback control.
- Hỗ trợ config flow, chọn loa mặc định, sensor chẩn đoán và các service automation.
- Kết nối add-on YouTube Pro qua API local trên cổng `2032`.
- Giữ token Integration riêng; không nhúng PayOS, database hoặc admin secret.
