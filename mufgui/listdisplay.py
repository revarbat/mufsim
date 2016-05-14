try:  # Python 2
    from Tkinter import *  # noqa
except ImportError:  # Python 3
    from tkinter import *  # noqa


class ListDisplay(Text):
    def __init__(self, master, readonly=False, gutter=0, **kwargs):
        self.frame = Frame(
            master,
            borderwidth=1,
            highlightthickness=0,
            relief=SUNKEN,
        )
        self.vbar = Scrollbar(
            self.frame,
            orient=VERTICAL,
            command=self.yview,
        )

        opts = dict(
            relief=SUNKEN,
            borderwidth=0,
            highlightthickness=0,
            wrap=NONE,
        )
        if readonly:
            opts['insertontime'] = 0
            opts['takefocus'] = 0
            opts['cursor'] = 'arrow'

        for k, v in opts.items():
            kwargs[k] = kwargs.get(k, v)

        Text.__init__(
            self,
            self.frame,
            yscrollcommand=self.yscroll_main,
            **kwargs
        )
        self.tag_config("sel", foreground="black")
        self.tag_config("lmargin", lmargin1="3p", lmargin2="3p")

        self.gutter = None
        self.gutter_width = gutter
        self.gutter_timer = None
        if gutter > 0:
            self.gutter = Text(
                self.frame,
                width=gutter,
                highlightthickness=0,
                takefocus=False,
                insertontime=0,
                borderwidth=0,
                yscrollcommand=self.yscroll_gutter,
                background="gray75",
                foreground="black",
                cursor="arrow",
                font=self.cget("font"),
            )
            self.gutter.bind("<Key>", lambda e: "break")
            self.gutter.bind("<<Cut>>", lambda e: "break")
            self.gutter.bind("<<Clear>>", lambda e: "break")
            self.gutter.bind("<<Paste>>", lambda e: "break")
            self.gutter.bind("<<PasteSelection>>", lambda e: "break")
            self.gutter.bind('<Double-Button-1>', lambda e: "break")
            self.gutter.pack(side=LEFT, fill=Y, expand=0)
            self.schedule_gutter_update()

        Text.pack(self, side=LEFT, fill=BOTH, expand=1)
        self.vbar.pack(side=LEFT, fill=Y, expand=0)
        self.bind("<Key>", self.schedule_gutter_update)

        if readonly:
            self.bind("<Key>", lambda e: "break")
            self.bind("<<Cut>>", lambda e: "break")
            self.bind("<<Clear>>", lambda e: "break")
            self.bind("<<Paste>>", lambda e: "break")
            self.bind("<<PasteSelection>>", lambda e: "break")
            self.bind('<Double-Button-1>', lambda e: "break")

    def yscroll_main(self, first, last):
        if self.gutter and self.yview() != self.gutter.yview():
            self.gutter.yview_moveto(first)
        self.vbar.set(first, last)

    def yscroll_gutter(self, first, last):
        if self.yview() != self.gutter.yview():
            self.yview_moveto(first)

    def update_gutter(self):
        if not self.gutter:
            return
        self.gutter_timer = None
        self.tag_add('lmargin', '0.0', END)
        glast = int(float(self.gutter.index('end-1c')))
        tlast = int(float(self.index('end-1c')))
        if tlast == 1:
            self.gutter.delete('0.0', END)
            lnum = "%*d" % (self.gutter_width, 1)
            self.gutter.insert(END, lnum)
            return
        if float(self.gutter.index('end-1c')) > 1.0:
            self.gutter.insert(END, "\n")
        if glast > tlast:
            self.gutter.delete('%d.0' % (tlast + 1), END)
        else:
            while glast < tlast:
                glast += 1
                lnum = "%*d\n" % (self.gutter_width, glast)
                self.gutter.insert(END, lnum)
            self.gutter.delete('end-1c', END)

    def schedule_gutter_update(self, event=None):
        if self.gutter_timer:
            return
        self.gutter_timer = self.after_idle(self.update_gutter)

    def insert(self, *args, **kwargs):
        Text.insert(self, *args, **kwargs)
        self.schedule_gutter_update()

    def delete(self, *args, **kwargs):
        Text.delete(self, *args, **kwargs)
        self.schedule_gutter_update()

    def grid(self, *args, **kwargs):
        return self.frame.grid(*args, **kwargs)

    def pack(self, *args, **kwargs):
        return self.frame.pack(*args, **kwargs)

    def place(self, *args, **kwargs):
        return self.frame.place(*args, **kwargs)

    def indent_text(self, by=4):
        rng = self.tag_ranges("sel")
        if rng:
            sel_first = int(float(str(rng[0])))
            sel_last = int(float(self.index(str(rng[1]) + '-1c')))
            lines = range(sel_first, sel_last + 1)
            self.tag_remove('sel', '0.0', END)
        else:
            lines = [int(float(self.index('insert')))]
        for line in lines:
            line_start_idx = "%d.0" % line
            line_end_idx = "%d.end" % line
            txtline = self.get(line_start_idx, line_end_idx)
            currind = 0
            for ch in list(txtline):
                if ch == ' ':
                    currind += 1
                elif ch == '\t':
                    currind = 8*(1+int(currind//8))
                else:
                    break
            pfx = ' ' * (currind + by)
            txtline = pfx + txtline.lstrip()
            self.delete(line_start_idx, line_end_idx)
            self.insert(line_start_idx, txtline)
        if rng:
            self.tag_add(
                'sel',
                '%d.0' % sel_first,
                '%d.end+1c' % sel_last,
            )


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
