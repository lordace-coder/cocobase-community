"""
Analytics Dashboard Views for SQLAdmin

Custom views providing insights into:
- Revenue and payments
- User activity and growth
- Project usage and performance
- System health metrics
"""

from sqladmin import BaseView, expose
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.core.database import engine
from app.models import (
    Payment, User, Project, AppUser, Collection,
    FunctionExecution, CloudFunction, EmailLog,
    CronJob, CronJobRun, ApiUsageCounter,
    ProjectSubscription, PricingPlan
)


class DashboardOverview(BaseView):
    """Main overview dashboard with key metrics"""
    name = "Dashboard Overview"
    icon = "fa-solid fa-chart-pie"
    category = "Analytics"

    @expose("/dashboard-overview", methods=["GET"])
    async def overview_dashboard(self, request):
        with Session(engine) as db:
            today = datetime.now(timezone.utc)
            last_30_days = today - timedelta(days=30)
            last_7_days = today - timedelta(days=7)

            # Key platform metrics
            total_users = db.query(func.count(User.id)).scalar() or 0
            new_users_30d = db.query(func.count(User.id)).filter(
                User.created_at >= last_30_days
            ).scalar() or 0

            total_projects = db.query(func.count(Project.id)).scalar() or 0
            active_projects = db.query(func.count(Project.id)).filter(
                Project.active == True
            ).scalar() or 0

            # Revenue metrics
            total_revenue = db.query(func.sum(Payment.amount)).filter(
                Payment.status == "success"
            ).scalar() or 0
            revenue_30d = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.status == "success",
                    Payment.created_at >= last_30_days
                )
            ).scalar() or 0

            # Active subscriptions
            active_subs = db.query(func.count(ProjectSubscription.id)).filter(
                ProjectSubscription.is_active == True
            ).scalar() or 0

            # API usage
            api_usage_30d = db.query(func.sum(ApiUsageCounter.request_count)).filter(
                ApiUsageCounter.last_synced_at >= last_30_days
            ).scalar() or 0

            # Storage
            total_storage = db.query(func.sum(Project.storage_used_bytes)).scalar() or 0
            total_storage_gb = total_storage / (1024**3)

            # System health
            total_emails = db.query(func.count(EmailLog.id)).filter(
                EmailLog.created_at >= last_30_days
            ).scalar() or 0
            sent_emails = db.query(func.count(EmailLog.id)).filter(
                and_(
                    EmailLog.status == "sent",
                    EmailLog.created_at >= last_30_days
                )
            ).scalar() or 0
            email_success_rate = (sent_emails / max(total_emails, 1)) * 100

            # Recent activity
            recent_payments = db.query(
                Payment.reference,
                User.username,
                Payment.amount,
                Payment.created_at
            ).join(User, User.id == Payment.user_id).filter(
                Payment.status == "success"
            ).order_by(desc(Payment.created_at)).limit(5).all()

            recent_users = db.query(
                User.username,
                User.email,
                User.created_at
            ).order_by(desc(User.created_at)).limit(5).all()

        conversion_rate = (active_subs/max(total_users, 1)*100)

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/analytics/dashboard_overview.html",
            {
                "total_users": total_users,
                "new_users_30d": new_users_30d,
                "total_projects": total_projects,
                "active_projects": active_projects,
                "revenue_30d": revenue_30d,
                "total_revenue": total_revenue,
                "active_subs": active_subs,
                "api_usage_30d": api_usage_30d,
                "total_storage_gb": total_storage_gb,
                "total_emails": total_emails,
                "email_success_rate": email_success_rate,
                "conversion_rate": conversion_rate,
                "recent_payments": recent_payments,
                "recent_users": recent_users,
            }
        )


class RevenueAnalyticsView(BaseView):
    """Revenue and payment analytics"""
    name = "Revenue Analytics"
    icon = "fa-solid fa-chart-line"
    category = "Analytics"

    @expose("/revenue-analytics", methods=["GET"])
    async def revenue_dashboard(self, request):
        with Session(engine) as db:
            # Date ranges
            today = datetime.now(timezone.utc)
            last_30_days = today - timedelta(days=30)
            last_7_days = today - timedelta(days=7)

            # Total revenue
            total_revenue = db.query(func.sum(Payment.amount)).filter(
                Payment.status == "success"
            ).scalar() or 0

            # Revenue last 30 days
            revenue_30d = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.status == "success",
                    Payment.created_at >= last_30_days
                )
            ).scalar() or 0

            # Revenue last 7 days
            revenue_7d = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.status == "success",
                    Payment.created_at >= last_7_days
                )
            ).scalar() or 0

            # Total successful payments
            total_payments = db.query(func.count(Payment.id)).filter(
                Payment.status == "success"
            ).scalar() or 0

            # Failed payments
            failed_payments = db.query(func.count(Payment.id)).filter(
                Payment.status == "failed"
            ).scalar() or 0

            # Average payment amount
            avg_payment = db.query(func.avg(Payment.amount)).filter(
                Payment.status == "success"
            ).scalar() or 0

            # Top paying users
            top_users = db.query(
                User.username,
                User.email,
                func.sum(Payment.amount).label("total_spent"),
                func.count(Payment.id).label("payment_count")
            ).join(Payment, Payment.user_id == User.id).filter(
                Payment.status == "success"
            ).group_by(User.id, User.username, User.email).order_by(
                desc("total_spent")
            ).limit(10).all()

            # Revenue by plan
            revenue_by_plan = db.query(
                PricingPlan.name,
                func.sum(Payment.amount).label("revenue"),
                func.count(Payment.id).label("payment_count")
            ).join(Payment, Payment.plan_id == PricingPlan.id).filter(
                Payment.status == "success"
            ).group_by(PricingPlan.name).order_by(desc("revenue")).all()

            # Monthly revenue trend (last 6 months)
            monthly_revenue = db.query(
                func.date_trunc('month', Payment.created_at).label('month'),
                func.sum(Payment.amount).label('revenue'),
                func.count(Payment.id).label('count')
            ).filter(
                and_(
                    Payment.status == "success",
                    Payment.created_at >= today - timedelta(days=180)
                )
            ).group_by('month').order_by('month').all()

            # Active subscriptions
            active_subs = db.query(func.count(ProjectSubscription.id)).filter(
                ProjectSubscription.is_active == True
            ).scalar() or 0

            # Expired subscriptions (last 30 days)
            expired_subs = db.query(func.count(ProjectSubscription.id)).filter(
                and_(
                    ProjectSubscription.is_active == False,
                    ProjectSubscription.end_date >= last_30_days,
                    ProjectSubscription.end_date < today
                )
            ).scalar() or 0

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/analytics/revenue.html",
            {
                "total_revenue": total_revenue,
                "revenue_30d": revenue_30d,
                "revenue_7d": revenue_7d,
                "total_payments": total_payments,
                "failed_payments": failed_payments,
                "avg_payment": avg_payment,
                "top_users": top_users,
                "revenue_by_plan": revenue_by_plan,
                "monthly_revenue": monthly_revenue,
                "active_subs": active_subs,
                "expired_subs": expired_subs,
            }
        )



class UserAnalyticsView(BaseView):
    """User activity and growth analytics"""
    name = "User Analytics"
    icon = "fa-solid fa-users"
    category = "Analytics"

    @expose("/user-analytics", methods=["GET"])
    async def user_dashboard(self, request):
        with Session(engine) as db:
            today = datetime.now(timezone.utc)
            last_30_days = today - timedelta(days=30)
            last_7_days = today - timedelta(days=7)

            # Total platform users
            total_users = db.query(func.count(User.id)).scalar() or 0

            # New users last 30 days
            new_users_30d = db.query(func.count(User.id)).filter(
                User.created_at >= last_30_days
            ).scalar() or 0

            # New users last 7 days
            new_users_7d = db.query(func.count(User.id)).filter(
                User.created_at >= last_7_days
            ).scalar() or 0

            # Total app users across all projects
            total_app_users = db.query(func.count(AppUser.id)).scalar() or 0

            # App users created last 30 days
            app_users_30d = db.query(func.count(AppUser.id)).filter(
                AppUser.created_at >= last_30_days
            ).scalar() or 0

            # Verified email users
            verified_users = db.query(func.count(AppUser.id)).filter(
                AppUser.email_verified == True
            ).scalar() or 0

            # OAuth users
            oauth_users = db.query(func.count(AppUser.id)).filter(
                AppUser.oauth_provider.isnot(None)
            ).scalar() or 0

            # Users with projects
            users_with_projects = db.query(func.count(func.distinct(User.id))).join(
                Project, Project.user_id == User.id
            ).scalar() or 0

            # Users with active subscriptions
            users_with_subs = db.query(func.count(func.distinct(User.id))).join(
                Project, Project.user_id == User.id
            ).join(
                ProjectSubscription, ProjectSubscription.project_id == Project.id
            ).filter(
                ProjectSubscription.is_active == True
            ).scalar() or 0

            # User growth by month (last 6 months)
            user_growth = db.query(
                func.date_trunc('month', User.created_at).label('month'),
                func.count(User.id).label('count')
            ).filter(
                User.created_at >= today - timedelta(days=180)
            ).group_by('month').order_by('month').all()

            # App user growth by month
            app_user_growth = db.query(
                func.date_trunc('month', AppUser.created_at).label('month'),
                func.count(AppUser.id).label('count')
            ).filter(
                AppUser.created_at >= today - timedelta(days=180)
            ).group_by('month').order_by('month').all()

            # Most active users (by project count)
            most_active = db.query(
                User.username,
                User.email,
                func.count(Project.id).label('project_count')
            ).join(Project, Project.user_id == User.id).group_by(
                User.id, User.username, User.email
            ).order_by(desc('project_count')).limit(10).all()

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/analytics/user_analytics.html",
            {
                "total_users": total_users,
                "new_users_30d": new_users_30d,
                "new_users_7d": new_users_7d,
                "total_app_users": total_app_users,
                "app_users_30d": app_users_30d,
                "verified_users": verified_users,
                "oauth_users": oauth_users,
                "users_with_projects": users_with_projects,
                "users_with_subs": users_with_subs,
                "user_growth": user_growth,
                "app_user_growth": app_user_growth,
                "most_active": most_active,
            }
        )


class ProjectAnalyticsView(BaseView):
    """Project usage and performance analytics"""
    name = "Project Analytics"
    icon = "fa-solid fa-diagram-project"
    category = "Analytics"

    @expose("/project-analytics", methods=["GET"])
    async def project_dashboard(self, request):
        with Session(engine) as db:
            today = datetime.utcnow()
            last_30_days = today - timedelta(days=30)

            # Total projects
            total_projects = db.query(func.count(Project.id)).scalar() or 0

            # Active projects (with recent activity)
            active_projects = db.query(func.count(Project.id)).filter(
                Project.active == True
            ).scalar() or 0

            # Projects created last 30 days
            new_projects_30d = db.query(func.count(Project.id)).filter(
                Project.created_at >= last_30_days
            ).scalar() or 0

            # Total collections
            total_collections = db.query(func.count(Collection.id)).scalar() or 0

            # Total storage used (in GB)
            total_storage = db.query(func.sum(Project.storage_used_bytes)).scalar() or 0
            total_storage_gb = total_storage / (1024**3)

            # API usage last 30 days
            api_usage_30d = db.query(func.sum(ApiUsageCounter.request_count)).filter(
                ApiUsageCounter.last_synced_at >= last_30_days
            ).scalar() or 0

            # Most active projects by API usage
            most_active_projects = db.query(
                Project.name,
                User.username,
                func.sum(ApiUsageCounter.request_count).label('total_requests')
            ).join(
                ApiUsageCounter, ApiUsageCounter.project_id == Project.id
            ).join(
                User, User.id == Project.user_id
            ).group_by(
                Project.id, Project.name, User.username
            ).order_by(desc('total_requests')).limit(10).all()

            # Projects by storage usage
            storage_leaders = db.query(
                Project.name,
                User.username,
                Project.storage_used_bytes
            ).join(
                User, User.id == Project.user_id
            ).filter(
                Project.storage_used_bytes.isnot(None)
            ).order_by(desc(Project.storage_used_bytes)).limit(10).all()

            # Projects with most collections
            collection_leaders = db.query(
                Project.name,
                User.username,
                func.count(Collection.id).label('collection_count')
            ).join(
                Collection, Collection.project_id == Project.id
            ).join(
                User, User.id == Project.user_id
            ).group_by(
                Project.id, Project.name, User.username
            ).order_by(desc('collection_count')).limit(10).all()

            # Projects with cloud functions
            projects_with_functions = db.query(func.count(func.distinct(CloudFunction.project_id))).scalar() or 0

            # Total cloud functions
            total_functions = db.query(func.count(CloudFunction.id)).scalar() or 0

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/analytics/project_analytics.html",
            {
                "total_projects": total_projects,
                "active_projects": active_projects,
                "new_projects_30d": new_projects_30d,
                "total_collections": total_collections,
                "total_storage_gb": total_storage_gb,
                "api_usage_30d": api_usage_30d,
                "total_functions": total_functions,
                "projects_with_functions": projects_with_functions,
                "most_active_projects": most_active_projects,
                "storage_leaders": storage_leaders,
                "collection_leaders": collection_leaders,
            }
        )


class SystemHealthView(BaseView):
    """Platform-wide system health metrics for admin"""
    name = "System Health"
    icon = "fa-solid fa-heart-pulse"
    category = "Analytics"

    @expose("/system-health", methods=["GET"])
    async def health_dashboard(self, request):
        with Session(engine) as db:
            today = datetime.now(timezone.utc)
            last_24h = today - timedelta(hours=24)
            last_7d = today - timedelta(days=7)

            # Platform-wide cloud function stats (high-level only)
            total_functions = db.query(func.count(CloudFunction.id)).scalar() or 0
            total_executions = db.query(func.count(FunctionExecution.id)).scalar() or 0
            executions_24h = db.query(func.count(FunctionExecution.id)).filter(
                FunctionExecution.created_at >= last_24h
            ).scalar() or 0

            # Platform health - aggregated success rate
            successful_executions = db.query(func.count(FunctionExecution.id)).filter(
                FunctionExecution.status == "success"
            ).scalar() or 0
            success_rate = (successful_executions / max(total_executions, 1)) * 100

            # Cron job platform stats
            total_cron_jobs = db.query(func.count(CronJob.id)).scalar() or 0
            active_cron_jobs = db.query(func.count(CronJob.id)).filter(
                CronJob.is_active == True
            ).scalar() or 0
            cron_runs_24h = db.query(func.count(CronJobRun.id)).filter(
                CronJobRun.ran_at >= last_24h
            ).scalar() or 0

            # Email platform stats
            total_emails = db.query(func.count(EmailLog.id)).scalar() or 0
            emails_24h = db.query(func.count(EmailLog.id)).filter(
                EmailLog.created_at >= last_24h
            ).scalar() or 0
            sent_emails = db.query(func.count(EmailLog.id)).filter(
                EmailLog.status == "sent"
            ).scalar() or 0
            failed_emails = db.query(func.count(EmailLog.id)).filter(
                EmailLog.status == "failed"
            ).scalar() or 0
            email_success_rate = (sent_emails / max(total_emails, 1)) * 100

            # Database size metrics
            total_app_users = db.query(func.count(AppUser.id)).scalar() or 0
            total_collections = db.query(func.count(Collection.id)).scalar() or 0

            # Platform usage trend (executions per day, last 7 days)
            daily_executions = db.query(
                func.date_trunc('day', FunctionExecution.created_at).label('day'),
                func.count(FunctionExecution.id).label('count')
            ).filter(
                FunctionExecution.created_at >= last_7d
            ).group_by('day').order_by('day').all()

            # Email delivery trend (last 7 days)
            daily_emails = db.query(
                func.date_trunc('day', EmailLog.created_at).label('day'),
                func.count(EmailLog.id).label('count')
            ).filter(
                EmailLog.created_at >= last_7d
            ).group_by('day').order_by('day').all()

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/analytics/system_health.html",
            {
                "total_functions": total_functions,
                "total_executions": total_executions,
                "executions_24h": executions_24h,
                "success_rate": success_rate,
                "total_cron_jobs": total_cron_jobs,
                "active_cron_jobs": active_cron_jobs,
                "cron_runs_24h": cron_runs_24h,
                "total_emails": total_emails,
                "emails_24h": emails_24h,
                "email_success_rate": email_success_rate,
                "failed_emails": failed_emails,
                "total_app_users": total_app_users,
                "total_collections": total_collections,
                "daily_executions": daily_executions,
                "daily_emails": daily_emails,
            }
        )
