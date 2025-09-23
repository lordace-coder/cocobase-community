from fastapi import Request
from fastapi.responses import RedirectResponse
from app.models import User
from sqladmin import ModelView, action


# todo implement sending of email

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]
    page_size = 100

    @action(
        name="send-email",
        label="Send Email",
        add_in_list=True,  # Add this action to the list view
    )
    async def send_email_action(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        # 'id' is a list of the primary keys (PKs) of the selected rows

        # 1. Get the email content from a form (or a new page)
        # For simplicity, we'll assume the email content is hardcoded or comes from
        # a more advanced form.
        subject = "Your Custom Subject"
        body = "Hello, this is a message from the admin panel!"

        # 2. Fetch the selected users from the database
        # session = request.state.session
        # stmt = select(User).where(User.id.in_(id))

        # result = await session.execute(stmt)
        # users = result.scalars().all()

        # # 3. Send emails to each user
        # recipients = [user.email for user in users]

        # message = MessageSchema(
        #     subject=subject,
        #     recipients=recipients,
        #     body=body,
        #     subtype="html"
        # )

        try:
            # await fast_mail.send_message(message)
            # print(f"Emails sent successfully to: {recipients}")
            # Use request.send_json() or a redirect for success
            return RedirectResponse(
                request.url_for("admin:list", identity=self.identity), status_code=303
            )
        except Exception as e:
            print(f"Error sending email: {e}")
            # Handle error (e.g., return a JSON error response)
            return RedirectResponse(
                request.url_for("admin:list", identity=self.identity), status_code=303
            )
