import json
import re
import sys
import argparse


def convert_req2json(req_input: str):

    requisitos = []
    variables = []
    observables = {}
    requirements = []
    obs_regexp = re.compile(r"(input|output|const|internal) (.*?) is (.*?)\s?$",
                            re.IGNORECASE)
    req_regexp = re.compile(r"(\S*): (.*?)\s?$")
    obsgroups = {'input': "input",
                 'output': "output",
                 'const': "constants",
                 'internal' : "internal"}

    for line in req_input.splitlines():
        # Comment -> Ignore
        if line.startswith("//") or line.startswith("#"):
            continue

        # Variable definition
        obs_matches = obs_regexp.findall(line)
        if obs_matches:
            try:
                obstype, varname, type_or_value = obs_matches[0]
            except ValueError:
                continue

            obstype = obsgroups[obstype.lower()]
            fieldname = "value" if obstype == "constant" else "type"
            variables.append({"nombre":varname, "tipo_objeto":obstype, "tipo_valor": type_or_value})
            continue
        # Requirement
        req_matches = req_regexp.findall(line)
        if req_matches:
            try:
                reqid, reqtext = req_matches[0]
            except ValueError:
                continue

            ambito = {}
            patron = {}

            texto_dividido = reqtext.split(",", 1)
            texto_ambito = texto_dividido[0]
            texto_patron = texto_dividido[1]

            ambito = create_ambito(texto_ambito, variables)
            patron = create_patron(texto_patron, variables)

            requisitos.append({"id_requisito": reqid, "ambito": ambito, "patron": patron})
            continue

    component = {"requisitos": requisitos}

    return json.dumps(component, indent=4)


def convert_req2json_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", nargs='?',
                    help=".req file to convert. Default read from stdin.")
    ap.add_argument("-o", "--output-file", type=str,
                    help="path to output file. Default output to stdout")
    args = ap.parse_args()

    if args.input_file:
        with open(args.input_file) as f:
            input_req = f.read()
    else:
        input_req = sys.stdin.read()

    output = convert_req2json(input_req)
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
    else:
        print(output)

def create_patron(text: str, list_variables: list):
    patron = {}
    predicados = []
    #obtenemos todos los predicados menos los de tiempo
    predicados_todos = re.findall('\".*?\"', text)
    
    #obtenemos todos los predicados de tiempo
    tiempos = re.findall('least .+? time', text)
    tiempos = tiempos + re.findall('than .+? time', text)
    tiempos = tiempos + re.findall('every .+? time', text)
    tiempos = tiempos + re.findall('most .+? time', text)

    #se quita la primera palabra del tiempo
    count_t = 0
    for t in tiempos:
    	if 'least' in t:
    		tiempos[count_t] = t.replace('least', '')
    	elif 'than' in t:
    		tiempos[count_t] = t.replace('than', '')
    	elif 'every' in t:
    		tiempos[count_t] = t.replace('every', '')
    	elif 'most' in t:
    		tiempos[count_t] = t.replace('most', '')
    	count_t += 1

    #se quita la segunda palabra del tiempo	
    count_t = 0
    for t in tiempos:
    	tiempos[count_t] = (t.replace('time', '')).strip()
    	#mirar si el predicado ya se encuentra en la lista para no introducirlo 2 veces
    	if tiempos[count_t] not in predicados_todos:
    		#si en el patron hay un afterwards y además es el primero de tiempo deberá meterlo en la posición 1
    		if 'afterwards' in text and count_t == 0:
    			predicados_todos.insert(1, tiempos[count_t])
    		else:
    			predicados_todos.append(tiempos[count_t])
    	count_t += 1


    #Tras obtener todos los predicados
    #se procede a sustituir el texto por su letra correspondiente
    count = 1
    text = text.replace('(','')
    text = text.replace(')','')
    text = text.replace('+', '')
    text = text.replace('|', '')
    text = text.replace('*', '')

    for pred in predicados_todos:
        pred = pred.replace('(','')
        pred = pred.replace(')','')
        pred = pred.replace('+' , '')
        pred = pred.replace('|', '')
        pred = pred.replace('*', '')

        if count == 1 :
            text = re.sub(pred, "{R}" , text , 1) 
        elif count == 2 :
            text = re.sub(pred, "{S}" ,text,1)
        elif count == 3 :
            text = re.sub(pred, "{T}" ,text,1)
        elif count == 4 :
            text = re.sub(pred, "{U}" ,text,1)

        count += 1

    #Tipo de patrón que es
    text = text.lstrip()
    tipos_predicados = type_patron(text)

    #lista de predicados que irán dentro del 
    predicados = []

    #introducir los predicados en la lista
    count_pred = 0
    for pred in predicados_todos:
    	if count_pred == 0:
    		text_pred = predicados_todos[0].replace('\"', '')
    		variables_using_predicado = variables_using(list_variables, text_pred)
    		predicados.append({"predicado": {"texto": text_pred, "indicador": "R", "tipo_predicado": tipos_predicados[0] , "variables": variables_using_predicado}})
    	elif count_pred == 1:
    		text_pred= predicados_todos[1].replace('\"', '')
    		variables_using_predicado = variables_using(list_variables, text_pred)
    		predicados.append({"predicado": {"texto": text_pred, "indicador": "S", "tipo_predicado": tipos_predicados[1] , "variables": variables_using_predicado}})
    	elif count_pred == 2:
    		text_pred = predicados_todos[2].replace('\"', '')
    		variables_using_predicado = variables_using(list_variables, text_pred)
    		predicados.append({"predicado": {"texto": text_pred, "indicador": "T", "tipo_predicado": tipos_predicados[2] , "variables": variables_using_predicado}})
    	elif count_pred == 3:
    		text_pred = predicados_todos[3].replace('\"', '')
    		variables_using_predicado = variables_using(list_variables, text_pred)
    		predicados.append({"predicado": {"texto": text_pred, "indicador": "U", "tipo_predicado": tipos_predicados[3] , "variables": variables_using_predicado}})
    	count_pred += 1

    patron = {"texto": text, "predicados": predicados}

    return patron


def create_ambito(text: str, list_variables: list):
	ambito = {}
	predicados = []
	predicados_todos = re.findall('\".*?\"', text)
	count = 1
	for pred in predicados_todos:
		if count == 1 :
			text = re.sub(pred, "{P}" , text , 1) 
		elif count == 2 :
			text = re.sub(pred, "{Q}" , text , 1)
		count += 1

    

	predicados = []

	count_pred = 0
	for pred in predicados_todos:
		if count_pred == 0:
			text_pred = predicados_todos[0].replace('\"', '')
			variables_using_predicado = variables_using(list_variables, text_pred)
			predicados.append({"predicado": {"texto": text_pred, "indicador": "P", "variables": variables_using_predicado}})
		elif count_pred == 1:
			text_pred = predicados_todos[1].replace('\"', '')
			variables_using_predicado = variables_using(list_variables, text_pred)
			predicados.append({"predicado": {"texto": text_pred, "indicador": "Q", "variables": variables_using_predicado}})
		count_pred += 1


	ambito = {"texto": text, "predicados": predicados}

	return ambito

def variables_using(list_variables: list, text: str):
	variables_return = []
	for var in list_variables:
		#if var.get('nombre') in text:
		if len(re.findall('\\b'+var.get('nombre')+'\\b', text)) > 0: 
			if var.get('nombre') not in variables_return:
				variables_return.append({'variable':{'nombre':var.get('nombre'), 'tipo': var.get('tipo_objeto'), "valor": var.get('tipo_valor')}})
	return variables_return

def type_patron(text: str):
    types_predicados = []
    if text == "it is always the case that if {R} holds, then {S} holds after at most {T} time units":
    	types_predicados = ["accionador", "accionante", "tiempo"]
    elif text == "it is always the case that if {R} holds, then {S} holds as well":
    	types_predicados =["accionador", "accionante"]
    elif text == "it is always the case that if {R} holds for at least {S} time units, then {T} holds afterwards":
    	types_predicados =["accionador", "tiempo", "accionante"]
    elif text == "it is always the case that {R} holds":
    	types_predicados =["accionante"]

    elif text == "it is never the case that {R} holds":
    	types_predicados = ["accionante"]
    return types_predicados
     

if __name__ == "__main__":
    convert_req2json_main()
