from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from typing import Optional
from contextlib import contextmanager

from app.core.config import settings
from app.core.security import create_verification_token

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.email_from_name = settings.EMAIL_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL
        self.debug_mode = settings.DEBUG

        if "@yandex." in self.smtp_user and not self.smtp_user.endswith("@yandex.ru"):
            logger.warning(f"Yandex email should be full address: {self.smtp_user}")

    @contextmanager
    def _create_connection(self) -> smtplib.SMTP:
        """Создать SMTP соединение с правильной настройкой TLS/SSL"""
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                logger.debug(f"Connected via SSL to {self.smtp_host}:{self.smtp_port}")
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                logger.debug(f"Connected to {self.smtp_host}:{self.smtp_port}")

            if self.debug_mode:
                server.set_debuglevel(1)

            if self.use_tls and not self.use_ssl:
                server.starttls()
                logger.debug("STARTTLS enabled")

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
                logger.debug(f"Authenticated as {self.smtp_user}")

            yield server

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication Error: {e}")
            raise
        except Exception as e:
            logger.error(f"SMTP Connection Error: {e}")
            raise
        finally:
            try:
                server.quit()
                logger.debug("SMTP connection closed")
            except:
                pass

    def send_email(
            self,
            to_email: str,
            subject: str,
            html_content: str,
            text_content: Optional[str] = None
    ) -> bool:
        """Основной метод отправки email"""
        if self.debug_mode and not getattr(settings, 'SEND_REAL_EMAILS', False):
            logger.info(f"[DEV MODE] Email would be sent to {to_email}")
            logger.info(f"Subject: {subject}")
            if text_content:
                logger.info(f"Text preview: {text_content[:200]}...")
            self._save_email_to_file(to_email, subject, html_content, text_content)
            return True

        if not self.smtp_user or not self.smtp_password:
            logger.error("SMTP credentials not configured!")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'{self.email_from_name} <{self.email_from}>'
            msg['To'] = to_email

            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Отправляем
            with self._create_connection() as server:
                server.send_message(msg)

            logger.info(f"Email successfully sent to {to_email}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP Error sending to {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False

    def send_verification_email(self, email: str, user_id: int) -> bool:
        """Отправить письмо для подтверждения email"""

        token = create_verification_token(user_id)

        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        subject = "Подтвердите ваш email для Family Circle"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background-color: white;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 40px 20px; 
                    text-align: center; 
                }}
                .content {{ 
                    padding: 40px 30px; 
                }}
                .button {{ 
                    display: inline-block; 
                    padding: 14px 32px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    margin: 25px 0;
                    font-weight: 600;
                    font-size: 16px;
                    border: none;
                    cursor: pointer;
                }}
                .code-box {{
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 20px 0;
                    word-break: break-all;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                }}
                .footer {{ 
                    text-align: center; 
                    margin-top: 40px; 
                    padding-top: 20px;
                    border-top: 1px solid #eaeaea;
                    font-size: 12px; 
                    color: #666; 
                }}
                @media (max-width: 600px) {{
                    .content {{ padding: 20px 15px; }}
                    .button {{ width: 100%; text-align: center; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">🎉 Добро пожаловать!</h1>
                    <p style="margin-top: 10px; opacity: 0.9;">Family Circle - ваша семейная история</p>
                </div>
                <div class="content">
                    <p style="font-size: 16px;">Здравствуйте!</p>
                    <p>Спасибо за регистрацию в <strong>Family Circle</strong>. 
                       Для активации аккаунта подтвердите ваш email адрес.</p>

                    <div style="text-align: center;">
                        <a href="{verify_url}" class="button">Подтвердить Email</a>
                    </div>

                    <p>Или скопируйте ссылку ниже:</p>
                    <div class="code-box">
                        {verify_url}
                    </div>

                    <p style="color: #666; font-size: 14px;">
                        ⏳ Ссылка действительна 24 часа.<br>
                        🔒 Если вы не регистрировались, проигнорируйте это письмо.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 Family Circle. Все права защищены.</p>
                    <p>Это автоматическое письмо, пожалуйста не отвечайте на него.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Добро пожаловать в Family Circle!

        Спасибо за регистрацию. Для активации аккаунта подтвердите ваш email.

        Подтвердить email: {verify_url}

        Если кнопка не работает, скопируйте ссылку в браузер.

        ⏳ Ссылка действительна 24 часа.
        🔒 Если вы не регистрировались, проигнорируйте это письмо.

        ---
        © 2026 Family Circle
        """

        return self.send_email(email, subject, html_content, text_content)

    def send_welcome_email(self, email: str, username: str) -> bool:
        """Отправить приветственное письмо после подтверждения"""
        subject = f"Добро пожаловать в Family Circle, {username}!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #4CAF50;">🎉 Добро пожаловать, {username}!</h1>
                <p>Ваш email успешно подтвержден. Теперь вы можете:</p>
                <ul>
                    <li>Войти в свой аккаунт</li>
                    <li>Начать создавать семейное древо</li>
                    <li>Делиться фотографиями и воспоминаниями</li>
                    <li>Приглашать родственников</li>
                </ul>
                <p>Начните прямо сейчас!</p>
                <p>С уважением,<br>Команда Family Circle</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(email, subject, html_content)

    def _save_email_to_file(self, to_email: str, subject: str,
                            html_content: str, text_content: Optional[str] = None):
        """Сохранить email в файл для тестирования (dev mode)"""
        import os
        from datetime import datetime

        logs_dir = "email_logs"
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{logs_dir}/email_{timestamp}_{to_email.replace('@', '_at_')}.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Time: {datetime.now()}\n")
            f.write("\n" + "=" * 50 + "\n\n")
            f.write(html_content)

        logger.info(f"📧 Email saved to file: {filename}")


# Создаем экземпляр с учетом настроек
if settings.DEBUG and not getattr(settings, 'SEND_REAL_EMAILS', False):
    logger.info("📧 Email service running in DEV mode (emails saved to files)")


    class MockEmailService:
        """Заглушка для разработки"""

        def send_email(self, to_email, subject, html_content, text_content=None):
            logger.info(f"[MOCK] Email to {to_email}: {subject}")
            EmailService()._save_email_to_file(to_email, subject, html_content, text_content)
            return True

        def send_verification_email(self, email, user_id):
            token = create_verification_token(user_id)
            verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            logger.info(f"[MOCK] Verification link for {email}: {verify_url}")
            return True

        def send_welcome_email(self, email, username):
            logger.info(f"[MOCK] Welcome email to {email} for {username}")
            return True


    email_service = MockEmailService()
else:
    email_service = EmailService()