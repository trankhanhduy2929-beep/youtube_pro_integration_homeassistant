# YouTube Pro custom integration 4.0.0

Custom integration này kết nối tới API biệt lập của add-on YouTube Pro. Bearer token chỉ có quyền trên `/api/integration/*`; các API quản trị khác vẫn giới hạn qua Home Assistant Ingress.

## Cài đặt

1. Chép thư mục `custom_components/youtube_pro` vào `/config/custom_components/youtube_pro`.
2. Khởi động lại Home Assistant.
3. Mở add-on **YouTube Pro → Hẹn giờ → Home Assistant integration**, chọn **Sao chép token**.
4. Trong Home Assistant, vào **Settings → Devices & services → Add integration → YouTube Pro**.
5. Nhập URL add-on, thường là `http://homeassistant.local:2032` hoặc `http://<IP_HOME_ASSISTANT>:2032`, token vừa sao chép và loa mặc định cho Media Browser.

Nếu tạo token mới trong add-on, Home Assistant sẽ mở luồng re-auth để nhập token mới.

Nếu nâng cấp từ 3.1.0, vào **Settings → Devices & services → YouTube Pro → Configure** để chọn loa mặc định.

## Media Browser

- Nguồn **YouTube Pro** xuất hiện trong Home Assistant Media Browser với playlist, hàng chờ, lịch sử, khám phá và tìm kiếm gần đây.
- Entity **YouTube Pro Media Browser** hỗ trợ ô Search native của Home Assistant; kết quả YouTube được phát qua playback engine tới loa mặc định.
- Có thể phát từng track từ nguồn Media Browser trên một `media_player` bất kỳ; integration resolve URL qua relay an toàn của add-on.
- Khi mở một playlist trên entity Media Browser ảo, chọn bài sẽ giữ ngữ cảnh playlist để next/previous/repeat/shuffle tiếp tục hoạt động.

## Entity

- Media Browser
- Health
- Extractor
- Resolve time
- Active sessions
- Transport

## Service

- `youtube_pro.play`
- `youtube_pro.play_playlist`
- `youtube_pro.enqueue`
- `youtube_pro.set_timer`

Đã kiểm thử import, browse, search, resolve, phát URL, phát playlist và playback control bằng Home Assistant `2026.2.3` trong môi trường tạm. Chưa kiểm thử riêng bản 4.0.0 trên loa thật; bản 3.1.0 trước đó đã được người dùng xác nhận hoạt động tốt.
