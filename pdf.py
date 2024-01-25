from decimal import Decimal

from fpdf import FPDF


class PDFReport(FPDF):

    def colored_table(self, headings, rows, order, col_widths=(50, 39, 35, 42)):
        self.set_fill_color(89, 147, 187)
        # цвет текста
        self.set_text_color(255)
        # цвет линий таблицы
        self.set_draw_color(0)
        # ширина линии
        self.set_line_width(0.3)
        # жирный шрифт
        self.set_font(style="B")
        for col_width, heading in zip(col_widths, headings):
            self.cell(col_width, 7, heading, 1, align="C", fill=True)
        self.ln()
        # Восстановление цвета и шрифта:
        self.set_fill_color(224, 235, 255)
        self.set_text_color(0)
        self.set_font()
        fill = False

        for row in rows:
            self.cell(col_widths[0], 6, row[0], 1, align="L", fill=fill)
            self.cell(col_widths[1], 6, str(row[1]), 1, align="L", fill=fill)
            self.cell(col_widths[2], 6, str(row[2]), 1, align="L", fill=fill)
            self.cell(col_widths[3], 6, str(row[3]), 1, align="R", fill=fill)
            self.ln()
            fill = not fill

        total_cost_before_discount = sum((item["price"] * item["quantity"] for item in order["items"]))
        discount = Decimal(0)

        if order["coupon"]:
            discount = Decimal(total_cost_before_discount) * (order['discount'] / Decimal(100))
            self.cell(col_widths[0], 6, f'"{order["coupon"]["code"]}" coupon ({order["coupon"]["discount"]}% off)',
                      "TLR", align="L", fill=True)
            self.cell(sum(col_widths[1:]), 6, f"-{discount:.2f}", "TLR", align="R", fill=True)
            self.ln()

        self.set_fill_color(89, 147, 187)
        self.set_text_color(255)

        self.cell(col_widths[0], 6, "Total", "TLR", align="L", fill=True)
        self.cell(sum(col_widths[1:]), 6, f'{Decimal(total_cost_before_discount) - discount}',
                  "TLR", align="R", fill=True)
        self.ln()
        self.cell(sum(col_widths), 0, "", "T")

    def configure_fonts(self):

        self.add_font("Sans", style="", fname="static/fonts/Noto_Sans/NotoSans-Regular.ttf")
        self.add_font("Sans", style="B", fname="static/fonts/Noto_Sans/NotoSans-Regular.ttf")
        self.add_font("Sans", style="I", fname="static/fonts/Noto_Sans/NotoSans-Regular.ttf")
        self.add_font("Sans", style="BI", fname="static/fonts/Noto_Sans/NotoSans-Regular.ttf")

    def get_report(self, order, filename=None):
        self.configure_fonts()
        self.add_page()

        self.set_font("Sans", "B", size=20)
        self.cell(20, 10, "My Shop")
        self.ln(10)

        self.set_font("Sans", size=12)
        self.cell(20, 10, f'Invoice {order["_id"]}')
        self.ln(5)

        self.set_text_color(100, 100, 100)
        self.cell(20, 10, f'{order["created"]}')
        self.ln(10)

        self.set_font("Sans", "B", size=15)
        self.set_text_color(0)
        self.cell(20, 10, "Bill to")
        self.ln(10)

        self.set_font("Sans", size=12)
        self.cell(20, 10, f'{order["first_name"]} - {order["last_name"]}')
        self.ln(5)
        self.cell(20, 10, f'{order["email"]}')
        self.ln(5)
        self.cell(20, 10, f'{order["address"]}')
        self.ln(5)
        self.cell(20, 10, f'{order["postal_code"]}, {order["city"]}')
        self.ln(10)

        self.set_font("Sans", "B", size=10)
        self.cell(20, 10, "Items bought")
        self.ln(10)

        table_data = []
        for item in order["items"]:
            table_data.append([item["product"]["name"], item["price"], item["quantity"],
                               item["price"] * item["quantity"]])
        headers = ['Product', 'Price', 'Quantity', 'Cost']
        self.colored_table(headers, table_data, order)

        self.ln(10)
        self.set_line_width(2)
        self.set_font("Sans", "B", size=24)
        if order["paid"]:
            color = (0, 255, 0)
            width = 30
        else:
            color = (255, 0, 0)
            width = 45

        self.set_text_color(*color)
        self.set_draw_color(*color)

        self.cell(width, 15, f'{"PAID" if order["paid"] else "UNPAID"}', "LTRB", align='C')

        return self.output(filename)


if __name__ == '__main__':
    from db import db
    from bson import ObjectId
    from asyncio import get_event_loop


    async def pdf():
        ord_collection = db['order']
        _id = '65198a77328b8a02d6c6948f'

        order = await ord_collection.find_one({"_id": ObjectId(_id)})

        report = PDFReport()
        report_binary = report.get_report(order, 'ord.pdf')


    get_event_loop().run_until_complete(pdf())
