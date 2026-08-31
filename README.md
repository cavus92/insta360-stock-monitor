# Insta360 Stock Monitor

Bu repository, Insta360 Türkiye mağazasındaki iki ürünü kontrol eder:

1. Insta360 Luna Ultra
2. Insta360 Mic Pro Transmitter

GitHub Actions her 5 dakikada bir çalışır. Shopify ürün JSON'undaki ilgili variant'ın `available` alanı kontrol edilir. Ürün `false -> true` geçişi yaptığında SMTP üzerinden tek bir e-posta gönderilir.

## GitHub Secrets

Repository > Settings > Secrets and variables > Actions > New repository secret bölümünden şunları ekleyin:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `ALERT_EMAIL`

Gmail için tipik değerler:

- SMTP_HOST = `smtp.gmail.com`
- SMTP_PORT = `465`
- SMTP_USERNAME = Gmail adresiniz
- SMTP_PASSWORD = Gmail App Password
- ALERT_EMAIL = Bildirimin gönderileceği e-posta adresi

Normal Gmail hesabı şifresini kullanmayın. Gmail App Password kullanın.

## İlk çalıştırma

Actions > Insta360 Stock Monitor > Run workflow.

İlk çalıştırmada mevcut stok durumu `state.json` içine kaydedilir. Böylece ürün zaten stoktayken sürekli e-posta gönderilmez.

Daha sonra:

- stok yok -> stok yok: mail yok
- stok yok -> stokta: 1 mail
- stokta -> stokta: mail yok
- stokta -> stok yok: mail yok
- tekrar stokta: yeniden 1 mail

## Önemli

GitHub Actions zamanlamaları nominal olarak 5 dakikalık minimum aralıkla kurulabilir ancak gerçek çalışma zamanı birkaç dakika gecikebilir. Bu nedenle sistem "tam saniyesinde" değil, periyodik stok kontrolü şeklinde çalışır.
