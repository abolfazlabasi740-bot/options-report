import unittest

from codal_export_engine import parse_monthly_activity_html, _number, _event_tags


def cell_row(values):
    return "<tr>" + "".join("<td>" + str(x) + "</td>" for x in values) + "</tr>"


class CodalExportParsingTests(unittest.TestCase):
    def test_persian_numbers_and_parentheses(self):
        self.assertEqual(_number("۱,۲۳۴"), 1234.0)
        self.assertEqual(_number("(۵۶۷)"), -567.0)
        self.assertEqual(_number("۰"), 0.0)

    def test_explicit_product_and_currency_export_sections(self):
        product_header = ["شرح"] + [""] * 25
        product_columns = ["نام محصول", "واحد"] + [""] * 24
        marker = ["فروش صادراتی:"] + [""] * 25
        product = ["کاتد", "تن"] + [""] * 11 + ["۰", "۲,۲۱۵", "۲۲,۱۵۹,۳۳۰,۴۷۴", "۴۹,۰۸۲,۹۱۷", "۳۲,۳۱۶", "۳۲,۱۳۵", "۱۸,۶۴۸,۴۹۹,۸۰۱", "۵۹۹,۲۷۷,۱۸۷"] + [""] * 5
        total = ["جمع فروش صادراتی", ""] + [""] * 11 + ["۰", "۰", "", "۴۹,۰۸۲,۹۱۷", "۰", "۰", "", "۵۹۹,۲۷۷,۱۸۷"] + [""] * 5
        # Force the known 26-column monthly activity layout.
        product = (product + [""] * 26)[:26]
        total = (total + [""] * 26)[:26]
        table0 = "<table>" + cell_row(product_header) + cell_row(product_columns) + cell_row(marker) + cell_row(product) + cell_row(total) + "</table>"

        currency_header = ["منابع ارزی"] + [""] * 22
        currency_columns = ["مبلغ ارزی", "نوع ارز"] + [""] * 21
        currency_row = ["فروش صادراتی", "یورو"] + [""] * 9 + ["۳۰,۸۰۵,۱۰۸", "۱,۸۳۶,۰۷۶", "۵۶,۵۶۰,۵۲۸", "۴۰۶,۶۱۲,۱۸۹", "۱,۶۷۲,۵۰۴", "۶۸۰,۰۶۰,۶۷۸"] + [""] * 6
        currency_row = (currency_row + [""] * 23)[:23]
        table3 = "<table>" + cell_row(currency_header) + cell_row(currency_columns) + cell_row(currency_row) + "</table>"

        html = table0 + "<table></table><table></table>" + table3
        result = parse_monthly_activity_html(html)
        self.assertEqual(result["status"], "EXPORT_DISCLOSED")
        self.assertTrue(result["product_sales"]["section_present"])
        self.assertEqual(result["product_sales"]["month_total_million_irr"], 49082917.0)
        self.assertEqual(result["product_sales"]["cumulative_total_million_irr"], 599277187.0)
        currencies = result["foreign_currency_sales"]["currencies"]
        self.assertEqual(currencies[0]["currency"], "یورو")
        self.assertEqual(currencies[0]["month_rial_amount_million_irr"], 56560528.0)

    def test_event_tags_are_descriptive_not_sentiment(self):
        self.assertIn("IMPORTANT_DISCLOSURE", _event_tags("افشای اطلاعات بااهمیت - انعقاد قرارداد"))
        self.assertIn("CONTRACT", _event_tags("افشای اطلاعات بااهمیت - انعقاد قرارداد"))
        self.assertEqual(_event_tags("اطلاعیه نامشخص"), ["OTHER_OFFICIAL_FILING"])

    def test_missing_export_section_is_not_assumed_zero(self):
        html = "<table><tr><td>تولید</td></tr></table>"
        result = parse_monthly_activity_html(html)
        self.assertEqual(result["status"], "EXPORT_SECTION_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
