# YouTube Pro Home Assistant Integration

Custom integration **YouTube Pro 5.0.1** cho Home Assistant. Integration này
kết nối tới add-on YouTube Pro đang chạy trên cổng `2032` và không dùng chung
config entry, token hoặc dữ liệu với bản YouTube Music Lite.

## Cài bằng HACS

1. Mở **HACS → Integrations**.
2. Chọn menu ba chấm → **Custom repositories**.
3. Nhập URL repository GitHub này và chọn loại **Integration**.
4. Cài **YouTube Pro** rồi khởi động lại Home Assistant.
5. Vào **Settings → Devices & services → Add integration → YouTube Pro**.

## Cài thủ công

Giải nén file `youtube_pro_manual.zip` từ GitHub Release vào thư mục cấu hình
Home Assistant. Kết quả phải là:

```text
/config/custom_components/youtube_pro/manifest.json
```

Sau đó khởi động lại Home Assistant.

## Cấu hình

1. Khởi động add-on **YouTube Pro 5.0.1** trên cổng `2032`.
2. Mở add-on → **Hẹn giờ → Home Assistant integration**.
3. Sao chép token Integration.
4. Trong config flow, để URL là `auto` (khuyến nghị). Integration tự dò endpoint qua Supervisor/DNS nội bộ; chỉ nhập URL thủ công khi mạng có cấu hình đặc biệt.

Nếu cần URL thủ công, dùng `http://homeassistant.local:2032` hoặc IP LAN của Home Assistant.

5. Dán token và chọn loa mặc định cho Media Browser.

## Tính năng

- Media Browser native: khám phá, playlist, queue, history và tìm kiếm gần đây.
- Khu vực **Video YouTube** riêng với thumbnail, media class video và resolve relay.
- Tìm kiếm YouTube native theo ngữ cảnh nhạc hoặc video.
- Phát nhạc/video hoặc playlist tới bất kỳ `media_player` nào; HomePod/AirPlay được add-on xử lý audio fallback.
- Next, previous, repeat, shuffle và resolve relay an toàn.
- Sensor: health, extractor, resolve time, active sessions và transport.
- Service: `youtube_pro.play`, `youtube_pro.play_playlist`,
  `youtube_pro.enqueue`, `youtube_pro.set_timer`.

## Cập nhật token

Nếu tạo token mới trong add-on, mở **Configure** trên integration để nhập lại
token. Token cũ sẽ không được dùng tiếp.

## Bản Lite

YouTube Pro dùng integration domain `youtube_pro` và cổng `2032`. Bản Lite giữ
domain riêng và cổng `2232`, có thể chạy song song.

## Phát hành

Repository này có workflow kiểm tra tự động. Khi tạo tag dạng `v5.0.1`, GitHub
Actions sẽ tạo các asset:

- `youtube_pro.zip`: asset HACS.
- `youtube_pro_manual.zip`: gói cài thủ công.
- `youtube_pro_homeassistant_v5.0.1_source.zip`: source repository.
- `SHA256SUMS.txt`: checksum.

Integration không chứa PayOS secret, database secret, Worker service token hoặc
mật khẩu Admin.
