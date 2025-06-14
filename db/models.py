import enum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.parser import get_mail_hash
from core.schemas import EachMail
from db.decorator import with_session
from db.engine import SessionLocal


class Base(DeclarativeBase):
    pass


class MailStateEnum(enum.Enum):
    """邮件处理状态"""

    UNPROCESSED = "unprocessed"  # 未处理
    PROCESSED = "processed"  # 已自动处理
    MANUAL = "manual"  # 人工处理


class MailState(Base):
    __tablename__ = "mail_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    mail_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )  # 哈希值，唯一且加索引
    state: Mapped[MailStateEnum] = mapped_column(
        Enum(MailStateEnum, name="mail_state_enum"),
        default=MailStateEnum.UNPROCESSED,
        nullable=False,
    )
    sheet_name: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # 工作表名称，索引加速查询

    @with_session
    def update_mail_state(
        session: SessionLocal, self, mail: EachMail, state: MailStateEnum
    ) -> None:
        """将处理结果写入数据库"""
        mail_hash = get_mail_hash(mail)
        mail_state = MailState(
            mail_hash=mail_hash,
            sheet_name=mail.sheet_name,
            state=state,
        )

        session.add(mail_state)
        session.commit()

    @with_session
    def is_mail_exists(session: SessionLocal, self, mail: EachMail) -> bool:
        """检查邮件是否已存在"""
        mail_hash = get_mail_hash(mail)
        return (
            session.query(MailState).filter_by(mail_hash=mail_hash).first() is not None
        )

    @with_session
    def count_sheet_name(session: SessionLocal, self, mail: EachMail) -> MailStateEnum:
        """获取当天sheet_name对应的数量"""
        mail_count = (
            session.query(MailState)
            .filter_by(sheet_name=mail.sheet_name, state=MailStateEnum.PROCESSED)
            .count()
        )

        return mail_count
