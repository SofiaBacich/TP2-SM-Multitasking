import re
import time
from os import system, name
from collections import OrderedDict
from enum import Enum
import sys

#Este programa debe correrse por consola para ingresar los archivos a ensamblar

def main():
    ensamblador = Ensamblador()
    procesador = Procesador()

    ejecutables = ensamblador.crearEjecutables()

    sistemaOperativo = SistemaOperativo(ejecutables, procesador)
    procesador.sistemaOperativo = sistemaOperativo

    if ensamblador.cantidadErrores() == 0:
       procesador.procesar()
       print("Todos los procesos se han completado satisfactoriamente")
    else:
       ensamblador.mostrarErrores()
    


class Ensamblador:
    def __init__(self):
        self.instruccionesConError = {}
        self.lineaActual = 1
        self.archivosIncluidos = []
        self.ejecutable = Ejecutable()


    def crearEjecutables(self):
        ejecutables = []
        for i in range(1, len(sys.argv)):
            archivo = sys.argv[i]
            ejecutables.append(self.ensamblar(archivo))
            self.ejecutable = Ejecutable()
            self.lineaActual = 1

        return ejecutables

    def ensamblar(self, nombreArchivo):    #Parsea el archivo y trabaja con el ejecutable
        archivo = open(nombreArchivo, "r")
        self.archivosIncluidos.append(nombreArchivo.upper())

        for linea in archivo:             
            linea = linea.upper().rstrip() #Con rstrip borro el ultimo caracter de cada linea (\n), y paso todo a mayuscula

            if linea != "":
                self.ejecutable.agregarInstruccionCodigoFuente(linea, self.lineaActual)
                
                if self.chequearSintaxis(linea, self.lineaActual, nombreArchivo):
                    matchEtiqueta = re.search(r":", linea)
                    matchInclude = re.search(r'^(INCLUDE)\s+"(\w+.\w+)"\s*$', linea)

                    if matchEtiqueta:                      #Si es etiqueta
                        self.parsearEtiqueta(linea, self.lineaActual)
                    elif matchInclude:
                        self.ensamblar(matchInclude.group(2))
                        self.lineaActual -= 1
                    else:
                        self.parsearInstruccion(linea, self.lineaActual)
                
                self.lineaActual += 1    

        archivo.close()
        self.chequearParametros(nombreArchivo)

        return self.ejecutable

    def chequearSintaxis(self, linea, numLinea, archivo):
        matchEtiqueta = re.search(r'^(\w+):\s*$', linea)
        matchFuncSinParam = re.search(r'^(RET)\s*$', linea)                                          
        matchFuncUnParam = re.search(r'^(JMP|JZ|JNZ|JLE|JGE|INC|DEC|PUSH|POP|CALL|INT|NEG)\s+(-?\w+)\s*$', linea)
        matchFuncDosParam = re.search(r'^(MOV|ADD|CMP)\s+\w+\s*,\s*\w+\s*$', linea)
        matchInclude = re.search(r'^(INCLUDE)\s+"(\w+.\w+)"\s*$', linea)

        if not(matchEtiqueta or matchFuncSinParam or matchFuncUnParam or matchFuncDosParam or matchInclude):
            self.agregarInstruccionConError((linea, "Error de sintaxis"), (numLinea, archivo))
        
        if matchEtiqueta:
            etiqueta = matchEtiqueta.group(1)
            etiquetas = self.ejecutable.lookUpTable

            if etiqueta in etiquetas.keys():
                matchEtiqueta = False
                self.agregarInstruccionConError((linea, "Etiqueta duplicada"), (numLinea, archivo))
        
        if matchInclude:
            nombreArchivo = matchInclude.group(2)
            if nombreArchivo in self.archivosIncluidos:
                    matchInclude = False
                    self.agregarInstruccionConError((linea, "Nombre de archivo duplicado"), (numLinea, archivo))

        return (matchEtiqueta or matchFuncSinParam or matchFuncUnParam or matchFuncDosParam or matchInclude)

    def chequearParametros(self, archivo):
        instrucciones = self.ejecutable.instrucciones
        etiquetas = self.ejecutable.lookUpTable

        for instruccion in instrucciones.items():
            numLinea = instruccion[0]
            nombreInst = instruccion[1].nombre

            instruccionCodigoFuente = self.ejecutable.codigoFuente[numLinea]

            if nombreInst == "JMP" or nombreInst  == "JZ" or nombreInst  == "JNZ" or nombreInst  == "JLE" or nombreInst  == "JGE" or nombreInst  == "CALL":
                etiqueta = instruccion[1].parametros[0]
                if not(etiqueta in etiquetas.keys()):
                    self.agregarInstruccionConError((instruccionCodigoFuente, "Etiqueta inexistente"), (numLinea, archivo))

            elif nombreInst == "INT":
                sysCall = instruccion[1].parametros[0]
                if not(re.search(r'^\d+$', sysCall)):
                    self.agregarInstruccionConError((instruccionCodigoFuente, "Numero de SysCall Incorrecto"), (numLinea, archivo))

            elif nombreInst != "NOOP" and nombreInst != "RET" and nombreInst != "PUSH":
                registro = instruccion[1].parametros[0]

                if not(re.search(r'^(AX|BX|CX|DX)$', registro)):
                    self.agregarInstruccionConError((instruccionCodigoFuente, "Registro inexistente"), (numLinea, archivo)) #TODO: Chequear bug que cuando incluimos un archivo y hay un error en el incluido, marca error dos veces, uno en el incluido y otro en el archivo en que se incluye

                if len(instruccion[1].parametros) > 1:
                    segundoParametro = instruccion[1].parametros[1]

                    if not(re.search(r'^(-?\d+|(AX|BX|CX|DX))$', segundoParametro)):
                        self.agregarInstruccionConError((instruccionCodigoFuente, "Segundo Parametro Incorrecto"), (numLinea, archivo))

    def agregarInstruccionConError(self, value, key):
        self.instruccionesConError.update({key:value})  #key= (numLinea, archivo) value = (instruccionCodigoFuente, tipoError)
    
    def parsearEtiqueta(self, etiqueta, numLinea):
        nombre = (re.search(r'\w+', etiqueta)).group()                     
        
        self.ejecutable.agregarEtiqueta(nombre, numLinea)                  
        self.parsearInstruccion("NOOP", numLinea)

    def parsearInstruccion(self, instruccion, numLinea):
        match = re.search(r"^(\w+)\s+([-?\w,\s]+)$", instruccion)             #Separo nombre y parametros
        if match:
            nombre = match.group(1)
            parametros = list(re.split(r"\s*,\s*", match.group(2)))
        else:
            nombre = instruccion
            parametros = []

        self.ejecutable.agregarInstruccion(nombre, parametros, numLinea)

    def cantidadErrores(self):
        return len(self.instruccionesConError)

    def mostrarErrores(self):
        print("Se han detectado", self.cantidadErrores(), "errores en el código:")

        for error in OrderedDict(sorted(self.instruccionesConError.items())).items():
            print("Error de tipo", error[1][1], "en la linea", error[0][0],"del archivo", error[0][1], ":", error[1][0])
            

class Ejecutable:
    def __init__(self):   #Constructor
        self.entryPoint = 1                      #Indice en el que debe empezar a ejecutar la lista de instrucciones parseada
        self.codigoFuente = {}                   #Instrucciones del CODIGO FUENTE, sin parsear
        self.instrucciones = {}                  #Parseadas
        self.lookUpTable = {}                    #DICCIONARIO de etiquestas:    etiqueta, n° de línea

        
    def agregarInstruccionCodigoFuente(self, instruccion, numLinea):
        self.codigoFuente.update({numLinea:instruccion})

    def quitarInstruccionCodigoFuente(self, numLinea):
        del self.codigoFuente[numLinea]

    def agregarInstruccion(self, nombre, parametros, numLinea):
        self.instrucciones.update({numLinea:self.inicializarInstruccion(nombre, parametros)})

    def quitarInstruccion(self, numLinea):
        del self.instrucciones[numLinea]

    def inicializarInstruccion(self, nombre, parametros):
        match nombre:
            case "MOV":
                return MOV(nombre, parametros)
            case "ADD":
                return ADD(nombre, parametros)
            case "JMP":
                return JMP(nombre, parametros)
            case "JZ":
                return JZ(nombre, parametros)
            case "JNZ":
                return JNZ(nombre, parametros)
            case "JLE":
                return JLE(nombre, parametros)
            case "JGE":
                return JGE(nombre, parametros)
            case "CMP":
                return CMP(nombre, parametros)
            case "INC":
                return INC(nombre, parametros)
            case "DEC":
                return DEC(nombre, parametros)
            case "PUSH":
                return PUSH(nombre, parametros)
            case "POP":
                return POP(nombre, parametros)
            case "CALL":
                return CALL(nombre, parametros)
            case "RET":
                return RET(nombre)
            case "INT":
                return INT(nombre, parametros)
            case "NEG":
                return NEG(nombre, parametros)
            case "NOOP":
                return NOOP(nombre)

    def agregarEtiqueta(self, nombre, numLinea):
        if nombre == "ENTRYPOINT":
            self.entryPoint = numLinea
        else:
            self.lookUpTable.update({nombre:numLinea})

    def mostrarInstrucciones(self, numLineaCursor):
        for instruccion in self.codigoFuente.items():
            if instruccion[0] == numLineaCursor:
                print("-->  ", end="")
            else:
                print("     ", end="")
            print(instruccion[1])

    def mostrarEtiquetas(self):
        print(self.lookUpTable.items())            


class Procesador:
    def __init__(self):
        self.ip = 0
        self.zFlag = 0
        self.cFlag = 0
        self.ax = 0
        self.bx = 0
        self.cx = 0
        self.dx = 0
        self.estado = Estado.Activo


    def procesar(self):
        visualizador = Visualizador(self)
        while(self.estado == Estado.Activo):
            visualizador.mostrarInstrucciones()
            self.procesoActivo.ejecutable.instrucciones[self.ip].procesar(self)
            visualizador.mostrarValoresProcesador()
            visualizador.mostrarMemoriaVideo()
            self.sistemaOperativo.clockHandler()
            time.sleep(2) #Aca esta el delay, temporizador o retardo, comente esta linea para que el programa corra mas rapido

    def activarProceso(self, proceso):
        self.procesoActivo = proceso
        self.procesoActivo.contadorInstrucciones = 0
        self.ax = proceso.contexto['ax']
        self.bx = proceso.contexto['bx']
        self.cx = proceso.contexto['cx']
        self.dx = proceso.contexto['dx']
        self.zFlag = proceso.contexto['zFlag']
        self.cFlag = proceso.contexto['cFlag']
        self.ip = proceso.contexto['ip']
        self.procesoActivo.estado = Estado.Activo

    def bloquearProceso(self):
        self.procesoActivo.contexto['ax'] = self.ax 
        self.procesoActivo.contexto['bx'] = self.bx
        self.procesoActivo.contexto['cx'] = self.cx
        self.procesoActivo.contexto['dx'] = self.dx
        self.procesoActivo.contexto['zFlag'] = self.zFlag
        self.procesoActivo.contexto['cFlag'] = self.cFlag
        self.procesoActivo.contexto['ip'] = self.ip
        self.procesoActivo.estado = Estado.Bloqueado

    def getRegistro(self, registro):
        match registro:
            case "AX":
                return self.ax
            case "BX":
                return self.bx
            case "CX":
                return self.cx
            case "DX":
                return self.dx
            case _:
                return "No es un registro"
            
    def setRegistro(self, registro, valor):
        match registro:
            case "AX":
                self.ax = valor
            case "BX":
                self.bx = valor
            case "CX":
                self.cx = valor
            case "DX":
                self.dx = valor

    def valorParametro(self, parametro):
        valor = self.getRegistro(parametro)
        if valor == "No es un registro":
            valor = parametro
        return int(valor)
 
    def mostrarValores(self):
        print("\nAX =", self.ax)
        print("\nBX =", self.bx)
        print("\nCX =", self.cx)
        print("\nDX =", self.dx)
        print("\nZFLAG =", self.zFlag)
        print("\nCFLAG =", self.cFlag)
        print("\nIP =", self.ip)
        print("\nStack =", self.procesoActivo.stack)


class Proceso:
    def __init__(self, ejecutable):
        self.stack = []
        self.memoriaVideo = [[ 0 for x in range( 10 )] for y in range( 10 )]
        self.ejecutable = ejecutable
        self.contexto = {'ax':0, 'bx':0, 'cx':0, 'dx':0, 'zFlag':0, 'cFlag':0, 'ip':ejecutable.entryPoint}
        self.contadorInstrucciones = 0
        self.estado = Estado.Bloqueado


class SistemaOperativo:
    def __init__(self, ejecutables, procesador): 
        self.procesos = []
        for ejecutable in ejecutables:
            self.procesos.append(Proceso(ejecutable))
        self.indiceProcesoActivo = 0

        self.procesador = procesador
        self.procesador.activarProceso(self.procesoActivo())

        self.RAFAGA_INSTRUCCIONES = 3

    def clockHandler(self):
        self.procesoActivo().contadorInstrucciones += 1

        if(self.procesoActivo().contadorInstrucciones >= self.RAFAGA_INSTRUCCIONES):        #Si Alcanza la rafaga de instrucciones, se bloquea
            self.procesador.bloquearProceso()

        if(self.procesador.ip > len(self.procesoActivo().ejecutable.instrucciones)):        #Finaliza el proceso (se corrieron todas sus instrucciones)
            self.procesoActivo().estado = Estado.Finalizado
            
        if(all( proceso.estado == Estado.Finalizado for proceso in self.procesos )):        #Finaliza el procesador (se finalizaron todos sus procesos)
            self.procesador.estado = Estado.Finalizado
        elif(self.procesoActivo().estado == Estado.Bloqueado or self.procesoActivo().estado == Estado.Finalizado):
                self.indiceProcesoActivo = self.indiceProcesoActivo + 1 if ( self.indiceProcesoActivo + 1 < len(self.procesos) ) else 0
                while(self.procesoActivo().estado == Estado.Finalizado):
                    self.indiceProcesoActivo = self.indiceProcesoActivo + 1 if ( self.indiceProcesoActivo + 1 < len(self.procesos) ) else 0
                
                self.procesador.activarProceso(self.procesoActivo())
        
    def syscallHandler(self, sysCall, parametros):
        if(sysCall == 1):
            entero = parametros[0]
            fila = parametros[1]
            columna = parametros[2]
            self.procesoActivo().memoriaVideo[fila][columna] = entero

    def procesoActivo(self):
        return self.procesos[self.indiceProcesoActivo]
        

class Estado(Enum):
    Activo = 1
    Bloqueado = 2
    Finalizado = 3


class Visualizador:
    def __init__(self, procesador):   #Constructor
        self.procesador = procesador


    def mostrarInstrucciones(self):
        clear()
        self.procesador.procesoActivo.ejecutable.mostrarInstrucciones(self.procesador.ip)

    def mostrarMemoriaVideo(self):
        print("Memoria de video:\n")
        for f in range(0, len(self.procesador.procesoActivo.memoriaVideo)):
            for c in range(0, len(self.procesador.procesoActivo.memoriaVideo)):
                print ("|" + str(self.procesador.procesoActivo.memoriaVideo[f][c]), end="")
            print("|")

    def mostrarValoresProcesador(self):  
        self.procesador.mostrarValores()
        

class Instruccion:
    def __init__(self, nombre, parametros):   #Constructor
        self.nombre = nombre
        self.parametros = parametros


    def imprimir(self):
        print(self.nombre, self.parametros)

    def procesar(self, procesador):
        pass                        #IP += 1


class MOV(Instruccion):
    def procesar(self, procesador):
        nombreDestino = self.parametros[0]
        
        valor = procesador.valorParametro(self.parametros[1])

        procesador.setRegistro(nombreDestino, valor)
        procesador.ip += 1


class ADD(Instruccion):
    def procesar(self, procesador):
        nombreDestino = self.parametros[0]
        valorDestino = int(procesador.getRegistro(nombreDestino))

        valor = procesador.valorParametro(self.parametros[1])

        procesador.setRegistro(nombreDestino, valorDestino + valor)
        procesador.ip += 1


class JMP(Instruccion):
    def procesar(self, procesador):
        etiqueta = self.parametros[0]
        numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]

        procesador.ip = numLinea

class JZ(Instruccion):
    def procesar(self, procesador):        
        if(procesador.zFlag == 0):
            etiqueta = self.parametros[0]
            numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]
            procesador.ip = numLinea
        else:
            procesador.ip += 1

class JNZ(Instruccion):
    def procesar(self, procesador):        
        if(procesador.zFlag != 0):
            etiqueta = self.parametros[0]
            numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]
            procesador.ip = numLinea
        else:
            procesador.ip += 1

class JLE(Instruccion):
    def procesar(self, procesador):        
        if(procesador.zFlag == 1 or procesador.cFlag == 1):
            etiqueta = self.parametros[0]
            numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]
            procesador.ip = numLinea
        else:
            procesador.ip += 1

class JGE(Instruccion):
    def procesar(self, procesador):        
        if(procesador.cFlag == 0):
            etiqueta = self.parametros[0]
            numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]
            procesador.ip = numLinea
        else:
            procesador.ip += 1

class CMP(Instruccion):
    def procesar(self, procesador):
        valorUno = procesador.getRegistro(self.parametros[0])
        
        valorDos = procesador.valorParametro(self.parametros[1])

        if valorUno == valorDos:
            procesador.zFlag = 1
            procesador.cFlag = 0
        elif valorUno < valorDos:
            procesador.zFlag = 0
            procesador.cFlag = 1
        else:
            procesador.zFlag = 0
            procesador.cFlag = 0

        procesador.ip += 1


class INC(Instruccion):
    def procesar(self, procesador):
        nombreDestino = self.parametros[0]
        valorDestino = int(procesador.getRegistro(nombreDestino))

        procesador.setRegistro(nombreDestino, valorDestino + 1)
        procesador.ip += 1


class DEC(Instruccion):
    def procesar(self, procesador):
        nombreDestino = self.parametros[0]
        valorDestino = int(procesador.getRegistro(nombreDestino))

        procesador.setRegistro(nombreDestino, valorDestino - 1)
        procesador.ip += 1


class PUSH(Instruccion):
    def procesar(self, procesador):
        valor = procesador.valorParametro(self.parametros[0])
        procesador.procesoActivo.stack.append(valor)

        procesador.ip += 1
    

class POP(Instruccion):
    def procesar(self, procesador):
        nombreDestino = self.parametros[0]
        valor = procesador.procesoActivo.stack.pop()

        procesador.setRegistro(nombreDestino, valor)
        procesador.ip += 1
    
    
class CALL(Instruccion):
    def procesar(self, procesador):
        direccionRetorno = procesador.ip + 1
        procesador.procesoActivo.stack.append(direccionRetorno)

        etiqueta = self.parametros[0]
        numLinea = procesador.procesoActivo.ejecutable.lookUpTable[etiqueta]

        procesador.ip = numLinea

    
class RET(Instruccion):
    def __init__(self, nombre):   #Constructor
        self.nombre = nombre


    def imprimir(self):
        print(self.nombre)

    def procesar(self, procesador):
        direccionRetorno = procesador.procesoActivo.stack.pop()
        procesador.ip = direccionRetorno

class INT(Instruccion):
    def procesar(self, procesador):
        sysCall = int(self.parametros[0])
        parametros = []
        if(sysCall == 1):
            entero = procesador.getRegistro("AX")
            fila = procesador.getRegistro("BX")
            columna = procesador.getRegistro("CX")
            parametros = [entero, fila, columna]
        
        procesador.sistemaOperativo.syscallHandler(sysCall, parametros)
        procesador.ip += 1

class NEG(Instruccion):
    def procesar(self, procesador):
        nombreRegisto = self.parametros[0]
        valorRegistro = int(procesador.getRegistro(nombreRegisto))
        procesador.setRegistro(nombreRegisto, valorRegistro * -1)

        procesador.ip += 1


class NOOP(Instruccion):   #Para representar las etiquetas
    def __init__(self, nombre):   #Constructor
        self.nombre = nombre


    def imprimir(self):
        print(self.nombre)

    def procesar(self, procesador):
        procesador.ip += 1



def clear():
    if name == 'nt':
        system('cls')   # For Windows
    else:
        system('clear') # For Mac and Linux (name is 'posix')

main()