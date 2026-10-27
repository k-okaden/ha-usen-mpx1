# USEN MPX-1 for Home Assistant

USEN の音楽放送チューナー **MPX-1** を Home Assistant から操作するカスタムインテグレーションです。
チューナー内蔵の Web リモコン (`http://<IP>/cgi-bin/*.cgi`) を LAN 経由で叩きます。クラウドは使いません。

## できること

| エンティティ | 内容 |
|---|---|
| `media_player.usen_mpx_1` | 電源 ON/OFF、音量 (0〜63)、チャンネル切替 (プリセット 1〜10 + AUX)、再生中の曲名・アーティスト |
| `sensor.usen_mpx_1_channel` | 現在のチャンネル名 |
| `sensor.usen_mpx_1_now_playing` | 再生中の曲 (`曲名 / アーティスト`) |
| `sensor.usen_mpx_1_next_track` | 次の曲 |
| `sensor.usen_mpx_1_volume` | 音量 (0〜63) |
| `sensor.usen_mpx_1_line_status` | 回線状態 (診断) |

サービス:

- `usen_mpx1.play_cue` — CUE 音源を再生 (`cue`: 1〜10, `volume`: -6〜+6, `repeat`, `mute_bgm`)
- `usen_mpx1.stop_cue` — CUE 再生を終了

```yaml
action: usen_mpx1.play_cue
target:
  entity_id: media_player.usen_mpx_1
data:
  cue: 9        # ラジオ体操
```

## インストール

### HACS (カスタムリポジトリ)

1. HACS → 右上メニュー → **カスタムリポジトリ** → `https://github.com/k-okaden/ha-usen-mpx1`、種類は **Integration**
2. 「USEN MPX-1」をダウンロードして Home Assistant を再起動

### 手動

`custom_components/usen_mpx1` を Home Assistant の `config/custom_components/` にコピーして再起動。

## 設定

**設定 → デバイスとサービス → 統合を追加 → USEN MPX-1** で IP アドレスを入力します。

IP を変えたときは、統合の **︙ → 再設定** から新しい IP を入力してください (MAC アドレスで同じ機器か確認します)。

> MPX-1 は DHCP クライアント ID (`01` + MAC) を送ってくるため、YAMAHA RTX などで固定するときは
> `dhcp scope bind <scope> <IP> ethernet <MAC>` の形式で予約してください。

## プロトコルメモ

すべて `Content-Type: application/x-www-form-urlencoded`、認証なし。

| 機能 | リクエスト | ボディ |
|---|---|---|
| 電源 ON / OFF | `POST /cgi-bin/power_on.cgi` / `power_off.cgi` | 空 |
| 音量 ±1 | `POST /cgi-bin/vol_chg.cgi` | `vol=1` (+1) / `vol=0` (-1)。応答は変更後の音量 (0〜63) |
| チャンネル | `POST /cgi-bin/chn_chg.cgi` | `chn=1`〜`10` (プリセット) / `chn=99` (AUX) |
| CUE | `POST /cgi-bin/cue_play.cgi` | `cue=1〜10&vol=0〜12&rep=0/1&muo=0/1&stt=0〜3` (stt: 0 設定 / 1 無音 / 2 再生 / 3 終了) |
| 状態 | `GET /data/home.csv` | 0 電源, 1 音量, 2 プリセット, 3 CH 名, 4 前の曲, 5 再生中, 6〜10 次の曲, 11〜 チューナー情報 |
| プリセット一覧 | `GET /cgi-bin/channel_print.cgi` | HTML (`ch{n}_str` / `ch{n}_num`)。電源 OFF 中は空 |

`examples/package_usen_mpx1.yaml` はインテグレーションを使わずに `rest_command` などで同じことをするパッケージ版です。

## 開発

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

USEN 公式のものではありません。自己責任で使ってください。
