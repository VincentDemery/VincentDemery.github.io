#!/usr/bin/env python2
import time, threading
from math import *
from subprocess import Popen, PIPE
import Tkinter

draw_numbers = False
width = 400

def open_file(filename, mode="r"): # <<<
    if filename.endswith(".gz"):
        if mode == "w":
            return Popen("gzip", stdin=PIPE, stdout=open(filename, "wb")).stdin
        else:
            return Popen(["gunzip", "-c", filename], stdout=PIPE).stdout
    else:
        return open(filename, mode)
# >>>


class Application(Tkinter.Frame):
    def __init__(self, filenames, width=width, master=None): # <<<
        Tkinter.Frame.__init__(self, master)
        self.filenames = filenames
        self.fileno = 0
        self.fileno_end = 0
        self.dumps = DumpReader()

        self.grid()
        self.createWidgets(width)
    # >>>
    def createWidgets(self, width): # <<<
        # read first header
        file = open_file(self.filenames[self.fileno], "r")
        self.dumps.read_header(file)
        ratio = ((self.dumps.boxbounds[1][1]-self.dumps.boxbounds[1][0]) /
                 (self.dumps.boxbounds[0][1]-self.dumps.boxbounds[0][0]))
        height = ratio*width

        # create widgets
        self.canvas = Canvas(self, width=width, height=height); self.canvas.grid(row=1)
        self.row2 = Tkinter.Frame(master=self); self.row2.grid(row=2)
        self.row3 = Tkinter.Frame(master=self); self.row3.grid(row=3)
        self.btn1 = Tkinter.Frame(master=self.row2); self.btn1.grid(row=1, column=3)
        self.btn2 = Tkinter.Frame(master=self.row2); self.btn2.grid(row=1, column=1)
        self.btn3 = Tkinter.Frame(master=self.row3); self.btn3.grid(row=1, column=3)
        self.btn4 = Tkinter.Frame(master=self.row3); self.btn4.grid(row=1, column=1)
        # spacers:
        Tkinter.Label(self.row2, text=" "*10).grid(row=1, column=2)
        Tkinter.Label(self.row3, text=" "*10).grid(row=1, column=2)
        # btn1
        Tkinter.Button(self.btn1, text='Quit', command=self.quit).grid()
        # btn2
        Tkinter.Button(self.btn2, text='Goto', command=self.goto).grid(row=1, column=0)
        self.counter = Tkinter.StringVar()
        self.counter.set("n=%d" % self.fileno)
        Tkinter.Entry(self.btn2, textvariable=self.counter).grid(row=1, column=1)
        Tkinter.Button(self.btn2, text='Prev', command=self.recede).grid(row=1, column=2)
        Tkinter.Button(self.btn2, text='Next', command=self.advance).grid(row=1, column=3)
        Tkinter.Button(self.btn2, text='Play', command=self.play).grid(row=1, column=4)
        Tkinter.Button(self.btn2, text='Stop', command=self.stop).grid(row=1, column=5)
        # btn3
        Tkinter.Button(self.btn3, text='Skip less', command=self.skipless).grid(row=1, column=0)
        self.every = Tkinter.IntVar()
        self.every.set(1)
        Tkinter.Label(self.btn3, textvariable=self.every).grid(row=1, column=1)
        Tkinter.Button(self.btn3, text='Skip more', command=self.skipmore).grid(row=1, column=2)
        # btn4
        Tkinter.Button(self.btn4, text='Slower', command=self.slower).grid(row=1, column=0)
        self.deltat = Tkinter.IntVar()
        self.deltat.set(2**7)
        Tkinter.Label(self.btn4, textvariable=self.deltat).grid(row=1, column=1)
        Tkinter.Button(self.btn4, text='Faster', command=self.faster).grid(row=1, column=2)

        # draw first atoms
        self.trafo = self.canvas.create_trafo(self.dumps, width, height)
        self.canvas.draw_frame(self.dumps, self.trafo)
        atoms = self.dumps.read_atoms(file)
        self.canvas.draw_atoms(atoms, self.trafo, self.dumps.radius)
        file.close()
    # >>>
    def replot(self): # <<<
        if self.fileno < self.fileno_end:
            self.fileno = min(self.fileno_end, self.fileno + self.every.get())
            self.counter.set("n=%d" % self.fileno)
            file = open_file(self.filenames[self.fileno])
            self.dumps.read_header(file)
            atoms = self.dumps.read_atoms(file)
            self.canvas.redraw_atoms(atoms, self.trafo, self.dumps.radius)
            file.close()
            self.canvas.update_idletasks()
            # loop until the final fileno is reached:
            if self.fileno < self.fileno_end:
                self.after(self.deltat.get(), self.replot)
    # >>>
    def advance(self): # <<<
        if self.fileno < len(self.filenames)-self.every.get():
            self.fileno_end = self.fileno + self.every.get()
            self.replot()
    # >>>
    def recede(self): # <<<
        if self.fileno > 0:
            self.fileno_end = self.fileno - self.every.get()
            self.fileno -= 2*self.every.get()
            self.replot()
    # >>>
    def play(self): # <<<
        self.fileno_end = len(self.filenames) - 1
        self.replot()
    # >>>
    def stop(self): # <<<
        self.fileno_end = self.fileno
    # >>>
    def goto(self): # <<<
        num = int(self.counter.get().split('=')[-1])
        self.fileno = num - 1
        self.fileno_end = num
        self.replot()
    # >>>
    def slower(self): # <<<
        self.deltat.set(self.deltat.get()*2)
    # >>>
    def faster(self): # <<<
        self.deltat.set(max(1, self.deltat.get()/2))
    # >>>
    def skipless(self): # <<<
        self.every.set(max(1, self.every.get()/2))
    # >>>
    def skipmore(self): # <<<
        self.every.set(self.every.get()*2)
    # >>>


class Canvas(Tkinter.Canvas):
    stddiskattrs = dict(fill="gray", outline="")
    bpdiskattrs = dict(fill="red", outline="")
    oriattrs = dict(arrow=Tkinter.LAST, width=6, arrowshape=(10,12,13))
    velattrs = dict(arrow=Tkinter.LAST, width=3, arrowshape=(10,12,6), fill="red")
    textattrs = dict(fill="blue", font=("Helvetica", 8))

    def __init__(self, master=None, dotext=draw_numbers, **kwattrs): # <<<
        Tkinter.Canvas.__init__(self, master, bg="white", **kwattrs)
        circles = []
        orivecs = []
        velocs = []
        texts = []
        self.velscale = None
        self.dotext = dotext
    # >>>
    def create_trafo(self, dumpreader, width, height): # <<<
        alpha = width / (dumpreader.boxbounds[0][1] - dumpreader.boxbounds[0][0])
        beta  = height / (dumpreader.boxbounds[1][1] - dumpreader.boxbounds[1][0])
        x0 = -alpha*dumpreader.boxbounds[0][0]
        y0 = beta*dumpreader.boxbounds[1][1]
        return lambda x, y: (x0+alpha*x, y0-beta*y)
    # >>>
    def draw_frame(self, dr, trafo): # <<<
        for s in [-1, 1]:
            x, y = s*0.5*dr.diagonal[0], s*0.5*dr.diagonal[1]
            for n, vec in zip(dr.initgrid, dr.initgridvectors):
                llx, lly = trafo(x, y)
                urx, ury = trafo(x-s*n*vec[0], y-s*n*vec[1])
                self.create_line(llx, lly, urx, ury)
    # >>>
    def draw_atoms(self, atoms, trafo, r): # <<<
        self.circles = [None for n in range(1+len(atoms))]
        self.orivecs = [None for n in range(1+len(atoms))]
        self.velocs  = [None for n in range(1+len(atoms))]
        self.texts   = [None for n in range(1+len(atoms))]
        for id, type, com, mass, r in atoms:
            llx, lly = trafo(com[0]-r, com[1]-r)
            urx, ury = trafo(com[0]+r, com[1]+r)
            if type == 1:
                attrs = self.stddiskattrs
            elif type == 2:
                attrs = self.bpdiskattrs
            self.circles[id] = self.create_oval(llx, lly, urx, ury, **attrs)
            #if ori:
            #    llx, lly = trafo(com[0]-r*ori[0], com[1]-r*ori[1])
            #    urx, ury = trafo(com[0]+r*ori[0], com[1]+r*ori[1])
            #    self.orivecs[id] = self.create_line(llx, lly, urx, ury, **self.oriattrs)
            #if vel:
            #    #velscale = 1.0/sqrt(vel[0]**2 + vel[1]**2)
            #    velscale = self.velscale
            #    llx, lly = trafo(com[0]-velscale*vel[0], com[1]-velscale*vel[1])
            #    urx, ury = trafo(com[0]+velscale*vel[0], com[1]+velscale*vel[1])
            #    self.velocs[id] = self.create_line(llx, lly, urx, ury, **self.velattrs)
            if self.dotext:
                llx, lly = trafo(com[0]-0.5*r, com[1])
                urx, ury = trafo(com[0]-0.5*r, com[1])
                self.texts[id] = self.create_text(llx, lly, text="%d" % (id-1), **self.textattrs)
    # >>>
    def redraw_atoms(self, atoms, trafo, r): # <<<
        for id, type, com, mass, r in atoms:
            llx, lly = trafo(com[0]-r, com[1]-r)
            urx, ury = trafo(com[0]+r, com[1]+r)
            self.coords(self.circles[id], llx, lly, urx, ury)
            #if ori:
            #    llx, lly = trafo(com[0]-r*ori[0], com[1]-r*ori[1])
            #    urx, ury = trafo(com[0]+r*ori[0], com[1]+r*ori[1])
            #    self.coords(self.orivecs[id], llx, lly, urx, ury)
            #if vel:
            #    #velscale = 1.0/sqrt(vel[0]**2 + vel[1]**2)
            #    velscale = self.velscale
            #    llx, lly = trafo(com[0]-velscale*vel[0], com[1]-velscale*vel[1])
            #    urx, ury = trafo(com[0]+velscale*vel[0], com[1]+velscale*vel[1])
            #    self.coords(self.velocs[id], llx, lly, urx, ury)
            if self.dotext:
                llx, lly = trafo(com[0]-0.5*r, com[1])
                urx, ury = trafo(com[0]-0.5*r, com[1])
                self.coords(self.texts[id], llx, lly)
    # >>>


class DumpReader:
    # <<<
    item_timestep             = "ITEM: TIMESTEP"
    item_temperature          = "ITEM: TEMPERATURE"
    item_number_of_atoms      = "ITEM: NUMBER OF ATOMS"
    item_initial_grid         = "ITEM: INITIAL GRID"
    item_initial_grid_vectors = "ITEM: INITIAL GRID VECTORS"
    item_box_bounds           = "ITEM: BOX BOUNDS"
    item_atoms                = "ITEM: ATOMS"
    radius = 0.5
    # >>>

    def __init__(self): # <<<
        self.time = None
        self.natoms = None
        self.ndim = None
        self.initgrid = None
        self.initgridvectors = None
        self.diagonal = None
        self.boxbounds = None

        # are there velocities and orientations in the dump file?
        self.have_ori = None
        self.have_vel = None
   # >>>
    def read_header(self, file): # <<<
        line = file.next()
        assert line.startswith(self.item_timestep)
        self.read_timestep(file)
        while True:
            line = file.next()
            line = line.strip() # strip trailing newline
            if line == self.item_number_of_atoms:
                self.read_number_of_atoms(file)
            elif line == self.item_temperature:
                self.read_temperature(file)
            elif line == self.item_initial_grid:
                self.read_initial_grid(file)
            elif line == self.item_initial_grid_vectors:
                self.read_initial_grid_vectors(file)
            elif line == self.item_box_bounds:
                self.read_box_bounds(file)
            elif line == self.item_atoms:
                break
            else:
                raise Exception("ERROR: found line \"%s\"" % line)
    # >>>
    def read_atoms(self, file): # <<<
        atoms = []
        for n in range(self.natoms):
            line = file.next().split()
            if self.have_ori is None:
                self.have_ori = (len(line) > 2+self.ndim)
                self.have_vel = (len(line) > 2+2*self.ndim)
            id = int(line[0])
            type = int(line[1])
            com = map(float, line[2:2+self.ndim])
            mass = float(line[2+self.ndim])
            radius = float(line[3+self.ndim])
            #ori = map(float, line[2+self.ndim:2+2*self.ndim])
            #vel = map(float, line[2+2*self.ndim:2+3*self.ndim])
            atoms.append((id, type, com, mass, radius))
        return atoms
    # >>>

    def read_timestep(self, file): # <<<
        self.time = float(file.next())
    # >>>
    def read_temperature(self, file): # <<<
        file.next()
    # >>>
    def read_number_of_atoms(self, file): # <<<
        if self.natoms is None:
            self.natoms = int(file.next())
        else:
            file.next()
    # >>>
    def read_initial_grid(self, file): # <<<
        if self.initgrid is None:
            self.initgrid = map(int, file.next().split())
            self.ndim = len(self.initgrid)
        else:
            file.next()
    # >>>
    def read_initial_grid_vectors(self, file): # <<<
        if self.initgridvectors is None:
            self.initgridvectors = []
            for dim in range(self.ndim):
                self.initgridvectors.append(map(float, file.next().split()))
            self.diagonal = map(float, file.next().split())
        else:
            for dim in range(self.ndim + 1):
                file.next()
    # >>>
    def read_box_bounds(self, file): # <<<
        if self.boxbounds is None:
            self.boxbounds = []
            for dim in range(self.ndim):
                self.boxbounds.append(map(float, file.next().split()))
                self.boxbounds[-1][0] -= 0.5
                self.boxbounds[-1][1] += 0.5
        else:
            for dim in range(self.ndim):
                file.next()
    # >>>


if __name__ == "__main__":
    import sys
    app = Application(sys.argv[1:])
    app.master.title("Sample application")
    app.mainloop()

# vim:foldmethod=marker:foldmarker=<<<,>>>
