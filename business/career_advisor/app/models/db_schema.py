"""
db_schema.py — PostgreSQL テーブル定義（SQLAlchemy ORM）

スプレッドシートの「列」として管理されていた項目を
リレーショナルDB構造に変換したスキーマ定義。

テーブル構成:
  students          — 学生マスタ（SF PersonAccount 相当）
  companies         — 企業マスタ（Notion 企業DB 相当）
  selection_statuses — 選考進捗（学生×企業 の N:N 中間テーブル）
  meeting_records   — 面談記録（SF Task 相当）
  action_items      — 次のアクション

依存パッケージ:
  pip install sqlalchemy psycopg2-binary alembic

接続文字列の設定例（.env）:
  DATABASE_URL=postgresql://user:password@localhost:5432/hr_support
"""

from __future__ import annotations

import os
import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Boolean, Date, DateTime, Text,
    ForeignKey, Integer, Enum, UniqueConstraint, Index,
    create_engine,
)
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy.sql import func

Base = declarative_base()

# ──────────────────────────────────────────────
# Enum 定義
# ──────────────────────────────────────────────

import enum


class SupportStatus(str, enum.Enum):
    """学生の支援ステータス（SF: Status__pc 相当）"""
    supporting   = "支援中"
    completed    = "支援終了"
    paused       = "一時停止"
    not_started  = "未着手"


class SupportPhase(str, enum.Enum):
    """学生の支援フェーズ（SF: Phase__pc 相当）"""
    initial_done     = "初回面談済"
    introduced       = "送客済"
    first_interview  = "一次面接"
    second_interview = "二次面接"
    final_interview  = "最終面接"
    offered          = "内定"
    declined         = "辞退"
    failed           = "不合格"


class SelectionPhase(str, enum.Enum):
    """選考フェーズ（選考進捗テーブル用）"""
    entry       = "エントリー"
    es          = "ES選考"
    web_test    = "Webテスト"
    first       = "一次面接"
    second      = "二次面接"
    final       = "最終面接"
    offered     = "内定"
    accepted    = "内定承諾"
    declined    = "辞退"
    failed      = "不合格"
    withdrawn   = "見送り"


class GraduationYear(str, enum.Enum):
    """卒業年度（SF: GraduationYears__pc 相当）"""
    y2025 = "25卒"
    y2026 = "26卒"
    y2027 = "27卒"
    y2028 = "28卒"
    y2029 = "29卒"


class FacultyCategory(str, enum.Enum):
    """学科区分（SF: Field19__c 相当）"""
    liberal    = "文系"
    electrical = "機電"
    chemistry  = "化生"
    arch       = "建築"
    it         = "情報"
    other      = "その他"


# ──────────────────────────────────────────────
# students — 学生マスタ
# ──────────────────────────────────────────────

class Student(Base):
    """
    学生マスタ。SF の PersonAccount（新卒RecordType）に相当。
    スプレッドシートの個人情報列を正規化して格納する。
    """
    __tablename__ = "students"

    id                = Column(String(36), primary_key=True, comment="UUID or SF Account ID")
    sf_account_id     = Column(String(20), unique=True, nullable=True, comment="SF Account ID (001...)")

    # 氏名
    last_name         = Column(String(50), nullable=False, comment="姓")
    first_name        = Column(String(50), nullable=True, comment="名")
    kana_last_name    = Column(String(50), nullable=True, comment="姓カナ")
    kana_first_name   = Column(String(50), nullable=True, comment="名カナ")

    # 連絡先
    email             = Column(String(200), nullable=True, comment="メールアドレス")
    phone             = Column(String(20), nullable=True, comment="携帯番号")

    # 学歴
    university_name   = Column(String(100), nullable=True, comment="大学名（自由記述）")
    university_sf_id  = Column(String(20), nullable=True, comment="大学SF参照ID (Field26__c)")
    faculty           = Column(String(100), nullable=True, comment="学部 (Field17__c)")
    department        = Column(String(100), nullable=True, comment="学科 (gakka__c)")
    faculty_category  = Column(
        Enum(FacultyCategory), nullable=True, comment="学科区分 (Field19__c)"
    )
    high_school       = Column(String(100), nullable=True, comment="高校名 (koukomei__pc)")
    graduation_year   = Column(
        Enum(GraduationYear), nullable=True, comment="卒業年度 (GraduationYears__pc)"
    )
    birth_date        = Column(Date, nullable=True, comment="生年月日 (seinengappi__c)")
    gender            = Column(String(10), nullable=True, comment="性別 (PersonGenderIdentity)")

    # 就活情報
    career_axis       = Column(Text, nullable=True, comment="就活の軸 (Field12__c)")
    gauchika          = Column(Text, nullable=True, comment="ガクチカ (Field13__c)")
    club_activities   = Column(Text, nullable=True, comment="所属サークル (Field22__c)")
    desired_industries = Column(Text, nullable=True, comment="志望業界 (Field1__c), カンマ区切り")
    desired_occupations = Column(Text, nullable=True, comment="希望職種 (DesiredOccupation__pc)")
    memo_direct       = Column(Text, nullable=True, comment="直紹介メモ (Field21__c)")

    # 支援管理
    support_status    = Column(
        Enum(SupportStatus), nullable=False,
        default=SupportStatus.supporting, comment="ステータス (Status__pc)"
    )
    support_phase     = Column(
        Enum(SupportPhase), nullable=True, comment="状況 (Phase__pc)"
    )
    advisor_name      = Column(String(50), nullable=True, comment="担当CA")
    interview_date    = Column(Date, nullable=True, comment="FS面談日 (InterviewDate__pc)")
    referrer          = Column(String(50), nullable=True, comment="紹介者 (ReportPerson__c)")
    cs_route          = Column(String(50), nullable=True, comment="CS経由 (CS_keiyu__c)")
    line_registered   = Column(Boolean, default=True, comment="公式LINE登録 (OfficialLineRegistration__pc)")

    # タイムスタンプ
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # リレーション
    selections        = relationship("SelectionStatus", back_populates="student", cascade="all, delete-orphan")
    meetings          = relationship("MeetingRecord", back_populates="student", cascade="all, delete-orphan")
    action_items      = relationship("ActionItem", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_students_sf_account_id", "sf_account_id"),
        Index("ix_students_name", "last_name", "first_name"),
    )

    def __repr__(self) -> str:
        return f"<Student {self.last_name}{self.first_name} ({self.sf_account_id})>"


# ──────────────────────────────────────────────
# companies — 企業マスタ
# ──────────────────────────────────────────────

class Company(Base):
    """
    企業マスタ。Notion 企業DB のページに相当。
    紹介対象企業の基本情報・選考フロー等を管理する。
    """
    __tablename__ = "companies"

    id               = Column(String(36), primary_key=True, comment="UUID or Notion page ID")
    notion_page_id   = Column(String(50), unique=True, nullable=True, comment="Notion page ID")

    name             = Column(String(200), nullable=False, comment="企業名")
    hp_url           = Column(String(500), nullable=True, comment="HP URL")
    business_summary = Column(Text, nullable=True, comment="事業概要")
    selection_flow   = Column(Text, nullable=True, comment="選考フロー")
    usp              = Column(Text, nullable=True, comment="USP・強み")
    persona          = Column(Text, nullable=True, comment="ペルソナ（求める人物像）")
    industry         = Column(String(100), nullable=True, comment="業界")
    employee_count   = Column(Integer, nullable=True, comment="従業員数")
    session_schedule = Column(Text, nullable=True, comment="説明会日程（JSON or テキスト）")

    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # リレーション
    selections       = relationship("SelectionStatus", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_companies_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Company {self.name}>"


# ──────────────────────────────────────────────
# selection_statuses — 選考進捗（学生×企業の中間テーブル）
# ──────────────────────────────────────────────

class SelectionStatus(Base):
    """
    学生と企業の選考進捗を管理する N:N 中間テーブル。
    スプレッドシートで「列」として管理されていた選考フェーズ・評価などを格納。

    SF の Task（活動記録）とは異なり、企業ごとの「現在の選考フェーズ」を表す。
    """
    __tablename__ = "selection_statuses"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    student_id     = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    company_id     = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    sf_record_id   = Column(String(20), nullable=True, comment="SF Activity/Task ID（参照用）")

    phase          = Column(
        Enum(SelectionPhase), nullable=False,
        default=SelectionPhase.entry, comment="選考フェーズ"
    )
    evaluation     = Column(String(10), nullable=True, comment="評価（S/A/B/C/D）")
    interview_date = Column(Date, nullable=True, comment="面接日")
    result_date    = Column(Date, nullable=True, comment="結果通知日")
    memo           = Column(Text, nullable=True, comment="メモ・特記事項")

    # スプレッドシートとの同期管理
    sheet_row_index = Column(Integer, nullable=True, comment="スプレッドシート上の行番号（1始まり）")
    last_synced_at  = Column(DateTime(timezone=True), nullable=True, comment="最終シート同期日時")
    sheet_status    = Column(String(100), nullable=True, comment="シートのステータス値（突合用）")

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # リレーション
    student        = relationship("Student", back_populates="selections")
    company        = relationship("Company", back_populates="selections")

    __table_args__ = (
        UniqueConstraint("student_id", "company_id", name="uq_student_company"),
        Index("ix_selection_phase", "phase"),
        Index("ix_selection_student", "student_id"),
    )

    def __repr__(self) -> str:
        return f"<SelectionStatus student={self.student_id} company={self.company_id} phase={self.phase}>"


# ──────────────────────────────────────────────
# meeting_records — 面談記録
# ──────────────────────────────────────────────

class MeetingRecord(Base):
    """
    面談記録。SF の Task（活動記録）に相当。
    tldv 議事録から自動生成された情報を格納する。
    """
    __tablename__ = "meeting_records"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    student_id     = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    sf_task_id     = Column(String(20), nullable=True, comment="SF Task ID（活動記録ID）")

    meeting_date   = Column(Date, nullable=False, comment="面談日")
    meeting_time   = Column(String(10), nullable=True, comment="面談時間（HH:MM形式）")
    advisor_name   = Column(String(50), nullable=True, comment="担当CA")
    meeting_count  = Column(Integer, nullable=True, comment="何回目の面談か")
    tldv_url       = Column(String(500), nullable=True, comment="tldv 議事録URL")

    summary        = Column(Text, nullable=True, comment="面談サマリー")
    impression     = Column(Text, nullable=True, comment="所感（自由記述）")
    next_actions_raw = Column(Text, nullable=True, comment="次のアクション（改行区切り）")

    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # リレーション
    student        = relationship("Student", back_populates="meetings")
    action_items   = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_meeting_student_date", "student_id", "meeting_date"),
    )

    def __repr__(self) -> str:
        return f"<MeetingRecord student={self.student_id} date={self.meeting_date}>"


# ──────────────────────────────────────────────
# action_items — アクションアイテム
# ──────────────────────────────────────────────

class ActionItem(Base):
    """
    面談で決まった「次のアクション」を1件1行で管理するテーブル。
    スプレッドシートでは1セルに改行区切りで書かれていたものを正規化。
    """
    __tablename__ = "action_items"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    student_id   = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    meeting_id   = Column(Integer, ForeignKey("meeting_records.id", ondelete="SET NULL"), nullable=True)

    description  = Column(Text, nullable=False, comment="アクション内容")
    due_date     = Column(Date, nullable=True, comment="期日")
    owner        = Column(String(50), nullable=True, comment="担当者（CA or 学生）")
    is_done      = Column(Boolean, default=False, comment="完了フラグ")
    done_at      = Column(DateTime(timezone=True), nullable=True, comment="完了日時")

    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    # リレーション
    student      = relationship("Student", back_populates="action_items")
    meeting      = relationship("MeetingRecord", back_populates="action_items")

    __table_args__ = (
        Index("ix_action_student_done", "student_id", "is_done"),
    )

    def __repr__(self) -> str:
        return f"<ActionItem student={self.student_id} due={self.due_date} done={self.is_done}>"


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def get_engine(database_url: Optional[str] = None):
    """
    SQLAlchemy Engine を作成して返す。
    database_url が省略された場合は DATABASE_URL 環境変数を使用する。

    Examples:
        engine = get_engine()
        Base.metadata.create_all(engine)  # テーブル作成
    """
    url = database_url or os.environ.get("DATABASE_URL", "")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL が未設定です。"
            ".env に DATABASE_URL=postgresql://user:pass@host/db を設定してください。"
        )
    return create_engine(url, echo=False, future=True)


def create_all_tables(database_url: Optional[str] = None) -> None:
    """全テーブルを作成する（開発・マイグレーション用）"""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    print(f"[db_schema] テーブルを作成しました: {list(Base.metadata.tables.keys())}")


# ──────────────────────────────────────────────
# スプレッドシート列 → DB フィールド のマッピングメモ
# ──────────────────────────────────────────────
#
# スプレッドシート列名          → DBテーブル.カラム
# ─────────────────────────────────────────────
# 学生名                        → students.last_name + first_name
# SFレコードID                  → students.sf_account_id
# ステータス                    → selection_statuses.phase
# 評価                          → selection_statuses.evaluation
# 面談日                        → meeting_records.meeting_date
# 次回面談日                    → action_items.due_date (owner=CA)
# 紹介元                        → students.referrer
# 担当CA                        → students.advisor_name
# 企業名                        → companies.name (via selection_statuses)
# 選考フェーズ                  → selection_statuses.phase
# 最終更新日時                  → selection_statuses.updated_at
# ─────────────────────────────────────────────
