from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignOnboarding(TransactionCase):
    """The onboarding course, created from data (not demo).

    The course is content, so the test proves it exists in a database loaded
    without demo data and that every section has its lessons.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env.ref("sign_onboarding.slide_channel_sign")

    def test_course_exists_and_is_published(self):
        """The course is a published training channel."""
        self.assertEqual(self.channel.name, "Signering i Vertel")
        self.assertEqual(self.channel.channel_type, "training")
        self.assertTrue(self.channel.is_published)

    def test_course_has_five_sections(self):
        """The course is built from five sections, as the manifest describes."""
        categories = self.channel.slide_ids.filtered("is_category")
        self.assertEqual(len(categories), 5)

    def test_every_section_has_lessons(self):
        """No section is empty — each one carries at least one lesson."""
        categories = self.channel.slide_ids.filtered("is_category")
        for category in categories:
            lessons = self.channel.slide_ids.filtered(
                lambda slide, category=category: not slide.is_category
                and slide.sequence > category.sequence
            )
            self.assertTrue(lessons, f"section {category.name} has no lessons")

    def test_lessons_are_articles_or_quizzes(self):
        """Lessons are readable content, not categories."""
        lessons = self.channel.slide_ids.filtered(lambda slide: not slide.is_category)
        self.assertTrue(lessons)
        self.assertTrue(
            all(lesson.slide_category in ("article", "quiz") for lesson in lessons),
            lessons.mapped("slide_category"),
        )
