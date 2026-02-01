from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from app.core.config import settings
from app.core.security import create_verification_token
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.email_from_name = settings.EMAIL_FROM_NAME

    def _create_connection(self) -> smtplib.SMTP:
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls()
        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)
        return server

    def send_email(
            self,
            to_email: str,
            subject: str,
            html_content: str,
            text_content: Optional[str] = None
    ) -> bool:
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not set, skipping email send")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'{self.email_from_name} <{self.email_from}>'
            msg['To'] = to_email

            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            with self._create_connection() as server:
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_verification_email(self, email: str, user_id: int) -> bool:
        token = create_verification_token(user_id)

        verify_url = f"{settings.BACKEND_URL}/auth/verify-email?token={token}"

        subject = "Подтвердите ваш email для Family Circle"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background-color: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Добро пожаловать в Family Circle!</h1>
                </div>
                <div class="content">
                    <p>Здравствуйте!</p>
                    <p>Спасибо за регистрацию в Family Circle. Для завершения регистрации 
                       пожалуйста подтвердите ваш email адрес.</p>
                    <p style="text-align: center;">
                        <a href="{verify_url}" class="button">Подтвердить Email</a>
                    </p>
                    <p>Или скопируйте эту ссылку в браузер:</p>
                    <p><code>{verify_url}</code></p>
                    <p>Ссылка действительна в течение 24 часов.</p>
                    <p>Если вы не регистрировались в Family Circle, просто проигнорируйте это письмо.</p>
                </div>
                <div class="footer">
                    <p>© 2026 Family Circle. Все права защищены.</p>
                    <p>Это письмо отправлено автоматически, пожалуйста не отвечайте на него.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Добро пожаловать в Family Circle!

        Спасибо за регистрацию. Для завершения регистрации пожалуйста подтвердите ваш email адрес.

        Перейдите по ссылке: {verify_url}

        Ссылка действительна в течение 24 часов.

        Если вы не регистрировались в Family Circle, просто проигнорируйте это письмо.

        © 2026 Family Circle
        """

        return self.send_email(email, subject, html_content, text_content)

    #def send_password_reset_email(self, email: str, user_id: int) -> bool:
        #"""Отправить письмо для сброса пароля"""


    def send_welcome_email(self, email: str, username: str) -> bool:
        """Отправить приветственное письмо после подтверждения"""
        subject = "Добро пожаловать в Family Circle!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Добро пожаловать, {username}!</h1>
            <p>Ваш email успешно подтвержден. Теперь вы можете войти в свой аккаунт.</p>
            <p>Начните создавать свое семейное древо и делиться воспоминаниями!</p>
        </body>
        </html>
        """

        return self.send_email(email, subject, html_content)


email_service = EmailService()