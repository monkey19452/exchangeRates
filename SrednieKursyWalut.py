import sys
from PyQt5.QtWidgets import (QWidget, QPushButton,QLabel, QGridLayout,QApplication,QListWidget, QListWidgetItem)#biblioteka do tworzenia okienka
import urllib.request, json #biblioteka urllib do pobierania danych z internetu  
import datetime as dt #data
import numpy as np #do obliczeń
import matplotlib.pyplot as plt #biblioteka z wykresami
"""
Program wczytuje plik json z nbp.pl zawierający nazwę waluty, jej skrót, kraj oraz kurs z ostatnich 45 dni.
Czasem zdarza się, że NBP nie aktualizuje codziennie kursu dla wybranych walut. W takim przypadku wyliczana jest
jej interpolowana wartosc co w programie zostało oznaczone gwiazdką.
Na wykres nanoszona jest krzywa pokazująca dokładny wykres (dokładny kurs, krzywa od punktu do punktu), następnie
względem tych "sztywnych" danych wyliczana jest aproksymacja, w celu przedtawinia kursu w bardziej "zaokrąglowny" sposób.
Oczywiscie obie linie znajdują sie jednoczesnie na wykresie, oś Y przedstawia kurs wybranej waluty względem PLN, oś X to dzień.
"""
#odczytanie pliku json z kursami walut oraz ustawienie kodowania polskich znaków(dla poprawnego wywietlania):
file = urllib.request.urlopen('http://api.nbp.pl/api/exchangerates/tables/a/last/30?format=json').read().decode('utf8')
wartosci = json.loads(file) # wczytanie pliku json który zawiera kursy walut

#interpolacja wielomianowa metodą Lagrange-a (źródło: wykład 4 z metod numerycznych)
def interpolacja_lagrange(x, y, xval): # xval: wartosc interpolowanej funkcji
    products = 0
    yval = 0
    for i in range(len(x)):
        products = y[i]
        for j in range(len(x)):
            if i != j:
                products = products * (xval - x[j]) / (x[i] - x[j])
        yval = yval + products
    return yval

#aproksymacja
def wierszeZamien(v,i,j):
    if len(v.shape) == 1:
        v[i],v[j] = v[j],v[i]
    else:
        v[[i,j],:] = v[[j,i],:]
     
def kolumnyZamien(v,i,j):
    v[:,[i,j]] = v[:,[j,i]]
  
def gauss(a, b, tol = 10000000000000000):
    n = len(b)
    s = np.zeros(n)
    for i in range(n):
        s[i] = max(np.abs(a[i,:]))
    
    for k in range(0, n-1):
        p = np.argmax(np.abs(a[k:n, k])/s[k:n])+k
        
        if abs(a[p, k])<tol:
            pass
        if p != k:
            wierszeZamien(b, k, p)
            wierszeZamien(s, k, p)
            wierszeZamien(a, k, p)
        
        for i in range(k+1, n):
            if a[i, k] != 0.0:
                lam = a[i, k]/a[k, k]
                a[i, k+1:n] = a[i, k+1:n]-lam*a[k, k+1:n]
                b[i] = b[i]-lam*b[k]
        
    if abs(a[n-1, n-1])<tol:
        pass
    
    b[n-1] = b[n-1]/a[n-1, n-1]
    for k in range(n-2, -1, -1):
        b[k] = (b[k]-np.dot(a[k, k+1:n], b[k+1:n]))/a[k, k] 
    return b

def polyFit(xData, yData, m):
    a = np.zeros((m+1, m+1))
    b = np.zeros(m+1)
    s = np.zeros(2*m+1)
    
    for i in range(len(xData)):
        temp = yData[i]
        for j in range(m+1):
            b[j] = b[j]+temp
            temp = temp*xData[i]
        temp = 1.0
        for j in range(2*m+1):
            s[j] = s[j]+temp
            temp = temp*xData[i]
    
    for i in range(m+1):
        for j in range(m+1):
            a[i, j] = s[i+j]
    
    return gauss(a, b)
  
 #tworzenie wykresu kursu wybranej waluty wartosć x dzien:   
def wykres(title, xData, yData, coeff, xlab = 'DZIEŃ', ylab = 'KURS WZGLĘDEM PLN'):
    m = len(coeff)
    x1 = min(xData)
    x2 = max(xData)
    dx = (x2-x1)/28.0 #krok funkcji aproksymacji (zielona)
    x = np.arange(x1, x2+dx/10.0, dx)
    y = np.zeros((len(x)))*1.0
    for i in range(m): #obliczanie wielomianu
        y = y+coeff[i]*x**i
    #
    plt.plot(xData, yData,'-r', label = u'Dokładny kurs')#czerwona łamana linia (dokładne położenie kursu na układzie wsp)
    plt.plot(x, y, '-g', label = u'Średni kurs')#zielona linia (wyliczona rednia z tej poprzedniej)
     #legenda:
    plt.legend()
    plt.legend(loc='right', bbox_to_anchor=(1, 1.15),#ustawienie legendy na wykresie
          fancybox=True, shadow=True, ncol=3)
    plt.xlabel(xlab); plt.ylabel(ylab)
    plt.grid(True)
    plt.title(title)
    plt.show()

instrukcja = """

1. WYBIERZ INTERESUJĄCĄ CIĘ WALUTĘ.

2. W OKNIE PROGRAMU ZOSTANĄ WYWIETLONE
    KURSY WZGLĘDEM POLSKIEGO ZŁOTEGO
    Z OSTATNICH 45 DNI.
   
3. DNI W KTÓRYCH NBP NIE PODAŁ KURSU 
    DANEJ WALUTY ZOSTAŁY OZNACZONE GWIAZDKĄ,
    W ICH MIEJSCE WYLICZONE ZOSTANĄ JEJ 
    WARTOŚCI INTERPOLOWANE.
   
4. WYKRES WYŚWIETLI APROKSYMOWANĄ
    (ZAOKRĄGLONĄ) FUNKCJĘ POKAZUJĄCĄ
    JAK ZMIENIAŁA SIĘ WARTOŚĆ DANEJ
    WALUTY W CIĄGU OSTATNICH 45 DNI
    WZGLĘDEM PLN.
 
"""+30*'\n' # seria nowych lini żeby okno nie "skakało" po wybraniu waluty i wcisnieciu OK

class Program(QWidget):
    
    def __init__(self):
        super().__init__()

        #Tworzenie okna programu:
        self.lbl1 = QLabel('Dostępne waluty:'+55*' ') #55 spacji zapewnia odpowiednią szerokosc okna (żeby nie przwijać okna w poziomie )
        self.lbl2 = QLabel() #chwilowo puste bo po kliknięciu OK w tym miejscu pojawi sie napis:"Kurs wybranej waluty" )
        self.lbl3 = QLabel(instrukcja)
        self.btn1 = QPushButton('OK')
        self.btn2 = QPushButton('Pomoc / Reset')
        self.list = QListWidget()
        #wyswietlanie danych (skrót, nazwa waluty) z pliku json:
        for i in range(len(wartosci[0]['rates'])):
            element = QListWidgetItem('%s (%s)' % (wartosci[0]['rates'][i]['code'], wartosci[0]['rates'][i]['currency']))
            self.list.addItem(element)
        
        #siatka z rozstawieniem elementów:
        siatkaOkna = QGridLayout()
        siatkaOkna.setSpacing(10)

        siatkaOkna.addWidget(self.lbl1, 0, 0)
        siatkaOkna.addWidget(self.list, 1, 0)
        siatkaOkna.addWidget(self.btn1, 2, 0)
        
        siatkaOkna.addWidget(self.lbl2, 0, 1)
        siatkaOkna.addWidget(self.lbl3, 1, 1)
        siatkaOkna.addWidget(self.btn2, 2, 1)
        
        self.setLayout(siatkaOkna)#włączenie siatki
        self.btn1.clicked.connect(self.wybranieWaluty)#wybranie waluty z listy
        self.btn2.clicked.connect(self.pomoc)#wcisniecie przycisku pomoc/reset
        self.setGeometry(300, 300, 100, 100)#ustawienie rozmiarów okna
        #szerokość 100 pozwala na dobranie minimalnej szerokości i wysokości okna
        self.setWindowTitle('Zestawienie kursów walut')
        self.show()

    def wybranieWaluty(self):
        
        wyswietlana_Waluta = self.list.currentRow()
        #konsola zawiera informacje które wartosci są interpolowane
        print(50*'.')
        print('Waluta: %s' %wartosci[0]['rates'][wyswietlana_Waluta]['currency'])
        print('Interpolowane wartości zawierają się pomiędzy podanymi datami:')
        temp = []
        yappr = []
        for i in range(len(wartosci)):
            #wskazanie zakresu interpolacji
            interpolacjaOdDo = (dt.datetime.strptime(wartosci[i]['effectiveDate'], '%Y-%m-%d') - dt.datetime.strptime(wartosci[i-1]['effectiveDate'], '%Y-%m-%d')).days
            if interpolacjaOdDo>1:
                j=0
                y = [wartosci[i-1]['rates'][wyswietlana_Waluta]['mid'], wartosci[i]['rates'][wyswietlana_Waluta]['mid']]
                x = [i for i in range(len(y))]
                xval = [i for i in np.arange(0, 1, 1/interpolacjaOdDo)]
                yval = []
                ytemp = []
                print('  %s - %s' % (wartosci[i-1]['effectiveDate'], wartosci[i]['effectiveDate']))
                for xv in xval:
                    data = (dt.datetime.strptime(wartosci[i]['effectiveDate'], '%Y-%m-%d')-dt.timedelta(days=interpolacjaOdDo-j)).__format__('%Y-%m-%d')
                    yval.append ('%s:***%.4f\n' % (data, interpolacja_lagrange(x, y, xv)))
                    ytemp.append(interpolacja_lagrange(x, y, xv))
                    j+=1
                for j in range(1, len(yval)):
                    temp.append(yval[j])
                    yappr.append(ytemp[j])
                temp.append ('%s:       %.4f\n' % (wartosci[i]['effectiveDate'], wartosci[i]['rates'][wyswietlana_Waluta]['mid']))
                yappr.append (wartosci[i]['rates'][wyswietlana_Waluta]['mid'])
            else:
                yappr.append (wartosci[i]['rates'][wyswietlana_Waluta]['mid'])
                temp.append ('%s:       %.4f\n' % (wartosci[i]['effectiveDate'],wartosci[i]['rates'][wyswietlana_Waluta]['mid']))
        print(50*'.')
        
        temp.reverse()
        text = ' '.join(temp)
        self.lbl3.setText(text)
        self.lbl2.setText("""
    Kurs wybranej waluty
                          
        Data:            Kurs: """)
        xappr = [i for i in range(0, len(yappr))]
        cf = polyFit(xappr, yappr, 6) 
        wykres('Kurs '+wartosci[0]['rates'][wyswietlana_Waluta]['code'], xappr, yappr, cf)

    def pomoc(self):
        #Przycisk pomoc/reset resetuje treśćdrugiej kolumny i powraca do pomocy     
        self.lbl2.setText('Wybierz walutę i kliknij OK')
        self.lbl3.setText(instrukcja)     

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Program()
    sys.exit(app.exec_())
