# YouTube Pro Home Assistant Integration

Custom integration **YouTube Pro 5.4.0** cho Home Assistant. Integration này
kết nối tới add-on YouTube Pro đang chạy trên cổng `2032` và không dùng chung
config entry, token hoặc dữ liệu với bản YouTube Music Lite.

## Cài bằng HACS

1. Mở **HACS → Integrations**.
2. Chọn menu ba chấm → **Custom repositories**.
3. Nhập URL repository GitHub này và chọn loại **Integration**.
4. Cài **YouTube Pro** rồi khởi động lại Home Assistant.
5. Vào **Settings → Devices & services → Add integration → YouTube Pro**.

## Cài thủ công

Sao chép thư mục `custom_components/youtube_pro` từ repository này vào thư mục
cấu hình Home Assistant. Kết quả phải là:

```text
/config/custom_components/youtube_pro/manifest.json
```

Sau đó khởi động lại Home Assistant.

## Cấu hình

1. Khởi động add-on **YouTube Pro 5.13.0** trên cổng `2032`.
2. Mở add-on → **Hẹn giờ → Home Assistant integration**.
3. Sao chép token Integration.
4. Trong config flow, để URL là `auto` (khuyến nghị). Integration tự dò endpoint qua Supervisor/DNS nội bộ; chỉ nhập URL thủ công khi mạng có cấu hình đặc biệt.

Nếu cần URL thủ công, dùng `http://homeassistant.local:2032` hoặc IP LAN của Home Assistant.

5. Dán token và chọn loa mặc định cho Media Browser.

### Nếu HACS báo `custom_components/None/manifest.json`

Xóa repository YouTube Pro khỏi **HACS → Custom repositories**, khởi động lại Home Assistant, rồi thêm lại đúng URL repository này với loại **Integration**. Không thêm URL release ZIP và không thêm thư mục con. HACS phải truy cập được cả `api.github.com` và `raw.githubusercontent.com`; lỗi `None` thường là cache cây repository cũ hoặc kết nối GitHub API bị timeout.

Nếu cần cài ngay, tải asset `youtube_pro-manual-v5.4.0.zip` trong release `v5.4.0`, giải nén thư mục `custom_components/youtube_pro` vào `/config/custom_components/youtube_pro`, rồi khởi động lại Home Assistant.

## Tính năng

- Media Browser native: khám phá, playlist, queue, history và tìm kiếm gần đây.
- Queue theo loa: xem và thao tác đúng danh sách tiếp theo của `media_player` đang chọn.
- Khu vực **Video YouTube** riêng với thumbnail, media class video và resolve relay.
- Tìm kiếm YouTube native theo ngữ cảnh nhạc hoặc video.
- Smart Radio từ bài đang phát (theo bài gốc + lịch sử), tự bổ sung đề xuất khi danh sách gần hết.
- Danh sách bài hát, playlist, hàng chờ và lịch sử trong Media Browser; không còn hồ sơ gu nghe.
- Không cần đăng nhập Google, Google OAuth hoặc đồng bộ tài khoản YouTube.
- Phát nhạc/video hoặc playlist tới bất kỳ `media_player` nào; HomePod/AirPlay được add-on xử lý audio fallback.
- Next, previous, repeat, shuffle và resolve relay an toàn.
- Sensor: health, extractor, resolve time, active sessions và transport.
- Service: `youtube_pro.play`, `youtube_pro.play_playlist`,
  `youtube_pro.enqueue`, `youtube_pro.start_radio`,
  `youtube_pro.pause`, `youtube_pro.resume`, `youtube_pro.set_timer`.
- Diagnostics: tải chẩn đoán config entry (token được che) tại
  **Settings → Devices & services → YouTube Pro → Download diagnostics**.
- Repair issue tự hiện khi không kết nối được add-on và tự biến mất khi kết nối lại.

## Cập nhật token

Nếu tạo token mới trong add-on, mở **Configure** trên integration để nhập lại
token. Token cũ sẽ không được dùng tiếp.

## Bản Lite

YouTube Pro dùng integration domain `youtube_pro` và cổng `2032`. Bản Lite giữ
domain riêng và cổng `2232`, có thể chạy song song.

## Riêng tư và an toàn

Integration này chỉ chứa mã cài đặt cần thiết. Nó không chứa PayOS secret,
database secret, Worker service token, license key hoặc mật khẩu Admin.

