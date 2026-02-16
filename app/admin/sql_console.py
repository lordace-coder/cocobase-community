"""
SQL Console for Admin Dashboard

Provides a read-only SQL query interface for database inspection.
Only allows SELECT queries for security.
"""

from sqladmin import BaseView, expose
from starlette.requests import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import SessionLocal
import re


class SQLConsoleView(BaseView):
    """Read-only SQL query console for admin"""
    name = "SQL Console"
    icon = "fa-solid fa-terminal"
    category = "Analytics"

    def is_read_only_query(self, query: str) -> tuple[bool, str]:
        """
        Check if query is read-only (SELECT only).
        Returns (is_valid, error_message)
        """
        # Remove comments and extra whitespace
        query_clean = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
        query_clean = query_clean.strip().upper()

        # Check for dangerous keywords
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'RENAME', 'GRANT', 'REVOKE',
            'EXECUTE', 'EXEC', 'CALL', 'MERGE', 'COPY'
        ]

        for keyword in dangerous_keywords:
            # Use word boundaries to avoid false positives
            if re.search(rf'\b{keyword}\b', query_clean):
                return False, f"Query contains forbidden keyword: {keyword}"

        # Must start with SELECT or WITH (for CTEs)
        if not (query_clean.startswith('SELECT') or query_clean.startswith('WITH')):
            return False, "Only SELECT queries are allowed"

        # Check for multiple statements (prevent injection)
        if ';' in query_clean[:-1]:  # Allow semicolon at end
            statements = [s.strip() for s in query_clean.split(';') if s.strip()]
            if len(statements) > 1:
                return False, "Multiple statements are not allowed"

        return True, ""

    @expose("/sql-console", methods=["GET", "POST"])
    async def sql_console(self, request: Request):
        """SQL console interface"""

        query = ""
        results = []
        columns = []
        error = None
        success_message = None
        execution_time = None

        if request.method == "POST":
            form_data = await request.form()
            query = form_data.get("query", "").strip()

            if query:
                # Validate query is read-only
                is_valid, error_msg = self.is_read_only_query(query)

                if not is_valid:
                    error = f"Security Error: {error_msg}"
                else:
                    # Execute query
                    session = SessionLocal()
                    try:
                        import time
                        start_time = time.time()

                        result = session.execute(text(query))

                        execution_time = round((time.time() - start_time) * 1000, 2)  # ms

                        # Fetch results
                        rows = result.fetchall()

                        if rows:
                            columns = list(result.keys())
                            results = [dict(zip(columns, row)) for row in rows]
                            success_message = f"Query executed successfully. {len(results)} rows returned in {execution_time}ms."
                        else:
                            success_message = f"Query executed successfully. No rows returned. ({execution_time}ms)"

                    except SQLAlchemyError as e:
                        error = f"Database Error: {str(e)}"
                    except Exception as e:
                        error = f"Error: {str(e)}"
                    finally:
                        session.close()

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/sql_console.html",
            {
                "query": query,
                "results": results,
                "columns": columns,
                "error": error,
                "success_message": success_message,
                "execution_time": execution_time,
                "result_count": len(results),
            }
        )
