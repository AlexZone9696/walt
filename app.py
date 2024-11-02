from flask import Flask, render_template, request, redirect, url_for, session, flash
from tronpy import Tron
from tronpy.keys import PrivateKey
import os

# Подключаемся к TRON Testnet (Nile)
client = Tron(network="nile")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Фиксированная комиссия за транзакцию
TRANSACTION_FEE = 0.5  # Комиссия в TRX

# Функция для создания нового кошелька
def create_wallet():
    private_key = PrivateKey.random()
    address = private_key.public_key.to_base58check_address()
    return private_key.hex(), address

# Маршрут для главной страницы
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для создания кошелька
@app.route('/create_wallet')
def create_wallet_route():
    private_key, address = create_wallet()
    session['private_key'] = private_key
    session['address'] = address
    return redirect(url_for('wallet'))

# Маршрут для входа в кошелек по приватному ключу
@app.route('/login_wallet', methods=['POST'])
def login_wallet():
    private_key = request.form.get('private_key')
    if private_key:
        try:
            key = PrivateKey(bytes.fromhex(private_key))
            address = key.public_key.to_base58check_address()
            session['private_key'] = private_key
            session['address'] = address
            return redirect(url_for('wallet'))
        except ValueError:
            flash("Неправильный приватный ключ")
            return redirect(url_for('index'))
    return redirect(url_for('index'))

# Функция для отправки TRX
def send_trx(private_key_hex, to_address, amount):
    private_key = PrivateKey(bytes.fromhex(private_key_hex))
    from_address = private_key.public_key.to_base58check_address()

    # Проверяем, достаточно ли средств для отправки
    total_amount = amount + TRANSACTION_FEE  # Сумма перевода + комиссия
    balance = client.get_account_balance(from_address)  # Баланс в TRX

    # Проверяем, достаточно ли средств
    if balance < total_amount:
        raise ValueError("Недостаточно средств для выполнения транзакции")

    # Создаем и подписываем транзакцию
    txn = (
        client.trx.transfer(from_address, to_address, int(amount * 1_000_000))  # Отправляем только запрашиваемую сумму
        .build()
        .sign(private_key)
    )
    txn.broadcast().wait()

    return txn.txid

# Маршрут для страницы кошелька
@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    if 'private_key' not in session:
        return redirect(url_for('index'))

    address = session.get('address')
    message = None

    try:
        # Получаем баланс в Sun
        balance = client.get_account_balance(address)  # Баланс в Sun
        balance_trx = balance / 1_000_000  # Баланс в TRX
    except Exception as e:
        balance = 0
        balance_trx = 0
        message = "Аккаунт еще не зарегистрирован в блокчейне. Баланс будет отображаться после первой транзакции."

    if request.method == 'POST':
        # Отправка TRX на другой адрес
        to_address = request.form.get('to_address')
        amount = float(request.form.get('amount'))
        private_key = session.get('private_key')
        try:
            txid = send_trx(private_key, to_address, amount)
            flash(f"Транзакция успешно отправлена! TxID: {txid}")
        except Exception as e:
            flash("Ошибка при отправке: " + str(e))

    return render_template('wallet.html', address=address, balance=balance, balance_trx=balance_trx, message=message)

if __name__ == '__main__':
    app.run(debug=True)
