from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignProjectTask(TransactionCase):
    """Sign requests attached to a project task.

    sign_project_task makes the task the record a request is about, and the
    company setting decides whether creating a task with a customer creates
    the request.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sign_template = cls.env["sign.oca.template"].create(
            {"name": "Task signature", "model_id": cls.env.ref("project.model_project_task").id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Task Customer"})
        cls.project = cls.env["project.project"].create({"name": "Signing project"})

    def test_company_can_point_at_a_task_sign_template(self):
        """The company setting is a sign template limited to project.task."""
        self.env.company.project_task_sign_oca_template_id = self.sign_template
        self.assertEqual(self.env.company.project_task_sign_oca_template_id, self.sign_template)

    def test_request_derives_task_and_project_from_record_ref(self):
        """task_id and project_id are computed from the request's record_ref."""
        task = self.env["project.task"].create(
            {"name": "Sign me", "project_id": self.project.id}
        )
        request = self.env["sign.oca.request"].create(
            {
                "name": "Request for the task",
                "template_id": self.sign_template.id,
                "record_ref": f"project.task,{task.id}",
                "data": b"JVBERi0xLjQK",
            }
        )
        self.assertEqual(request.task_id, task)
        self.assertEqual(request.project_id, self.project)
        self.assertEqual(task.sign_request_ids, request)
        self.assertEqual(task.sign_request_count, 1)

    def test_task_with_partner_generates_a_request(self):
        """Creating a task with a customer creates and sends a sign request."""
        self.env.company.project_task_sign_oca_template_id = self.sign_template
        task = self.env["project.task"].create(
            {
                "name": "Sign me too",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )
        self.assertEqual(task.sign_request_count, 1)
        self.assertEqual(task.sign_request_ids.record_ref, task)
        self.assertEqual(task.sign_request_ids.state, "sent")

    def test_task_without_template_generates_nothing(self):
        """Without a configured template a task with a customer stays unsigned."""
        self.env.company.project_task_sign_oca_template_id = False
        task = self.env["project.task"].create(
            {
                "name": "No template",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )
        self.assertEqual(task.sign_request_count, 0)
