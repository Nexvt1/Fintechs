let isRegisterMode = false;

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById('loginForm');
    if (form) form.setAttribute('novalidate', 'true');

    const ctaBtn = document.querySelector('.side-right .btn-outline');
    if (ctaBtn) {
        ctaBtn.setAttribute('onclick', 'toggleAuthMode()');
    }
});

function validateInputs(form) {
    clearTooltips();
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;

    for (let input of inputs) {
        if (!input.value.trim()) {
            showCustomTooltip(input, "Preencha este campo.");
            isValid = false;
            break; 
        }
    }
    return isValid;
}

function showCustomTooltip(inputElement, message) {
    if (!inputElement) return;
    inputElement.classList.add('input-error');
    inputElement.focus();

    const parent = inputElement.parentElement;
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f39c12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <span>${message}</span>
    `;
    parent.appendChild(tooltip);

    inputElement.addEventListener('input', () => {
        clearTooltips();
    }, { once: true });
}

function clearTooltips() {
    document.querySelectorAll('.custom-tooltip').forEach(el => el.remove());
    document.querySelectorAll('.input-error').forEach(el => el.classList.remove('input-error'));
}

function toggleAuthMode() {
    clearTooltips();
    isRegisterMode = !isRegisterMode;
    
    const loginForm = document.getElementById('loginForm');
    const title = document.querySelector('.side-left h1');
    const ctaTitle = document.querySelector('.side-right h1');
    const ctaDesc = document.querySelector('.side-right .sub-text');
    const ctaBtn = document.querySelector('.side-right .btn-outline');

    if (isRegisterMode) {
        title.innerText = "Criar Conta";
        ctaTitle.innerText = "Bem-vindo de volta!";
        ctaDesc.innerText = "Para se manter conectado conosco, faça login com suas informações.";
        ctaBtn.innerText = "ENTRAR";

        loginForm.innerHTML = `
            <label class="label">
                Nome de Usuário
                <input type="text" name="nome" id="regUsername" required class="input" placeholder="Seu nome">
            </label>
            <label class="label">
                E-mail
                <input type="email" name="email" id="regEmail" required class="input" placeholder="Seu e-mail">
            </label>
            <label class="label">
                Senha
                <input type="password" name="senha" id="regPassword" required class="input" placeholder="Crie uma senha">
            </label>
            <button type="submit" class="btn-primary">CADASTRAR</button>
        `;
        loginForm.onsubmit = handleRegister;
    } else {
        title.innerText = "Entrar";
        ctaTitle.innerText = "Seja bem-vindo!";
        ctaDesc.innerText = "Insira seus dados pessoais e comece sua jornada conosco";
        ctaBtn.innerText = "CADASTRAR-SE";

        loginForm.innerHTML = `
            <label class="label">
                Nome / Email
                <input type="text" name="login" id="loginInput" autocomplete="off" required class="input" placeholder="Nome ou Email">
            </label>
            <label class="label">
                Senha
                <input type="password" name="senha" id="loginPassword" required class="input" placeholder="Senha">
            </label>
            <a href="javascript:void(0)" class="forgot-link" onclick="toggleForgotCard(true)">Esqueceu sua senha?</a>
            <button type="submit" class="btn-primary">ENTRAR</button>
        `;
        loginForm.onsubmit = handleLogin;
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    if (!validateInputs(form)) return;

    const loginInputEl = document.getElementById('loginInput') || document.getElementById('loginEmail');
    const loginPasswordEl = document.getElementById('loginPassword');

    const loginVal = loginInputEl ? loginInputEl.value.trim() : '';
    const passwordVal = loginPasswordEl ? loginPasswordEl.value : '';

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: loginVal, login: loginVal, senha: passwordVal })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification("Login efetuado!", "Sua sessão foi iniciada com sucesso. Redirecionando...");
            if (data.user) {
                localStorage.setItem('usuario_logado', JSON.stringify(data.user));
            }
            // Redireciona para /home e a sessão permanece gravada
            setTimeout(() => {
                window.location.href = data.redirect || '/home';
            }, 1000);
        } else {
            showCustomTooltip(loginInputEl, data.erro || "E-mail/usuário ou senha incorretos.");
        }
    } catch (error) {
        console.error("Erro na requisição de login:", error);
        showNotification("Erro", "Não foi possível conectar ao servidor.");
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const form = event.target;
    if (!validateInputs(form)) return;

    const nomeEl = document.getElementById('regUsername');
    const emailEl = document.getElementById('regEmail');
    const senhaEl = document.getElementById('regPassword');

    const nome = nomeEl ? nomeEl.value.trim() : '';
    const email = emailEl ? emailEl.value.trim() : '';
    const senha = senhaEl ? senhaEl.value : '';

    try {
        const response = await fetch('/api/cadastro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, senha })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification("Conta criada!", `Bem-vindo, ${nome}! Sua conta foi registrada.`);
            setTimeout(() => {
                toggleAuthMode();
            }, 1500);
        } else {
            showCustomTooltip(emailEl, data.erro || "Erro ao realizar cadastro.");
        }
    } catch (error) {
        console.error("Erro no cadastro:", error);
        showNotification("Erro", "Erro ao conectar com o servidor.");
    }
}

function toggleForgotCard(show) {
    clearTooltips();
    const overlay = document.getElementById('forgotOverlay');
    if (!overlay) return;
    if (show) overlay.classList.add('active');
    else overlay.classList.remove('active');
}

function showNotification(title, message) {
    const titleEl = document.querySelector('.alert-title');
    const descEl = document.querySelector('.alert-desc');
    if (titleEl) titleEl.innerText = title;
    if (descEl) descEl.innerText = message;
    
    const notification = document.getElementById('successNotification');
    if (notification) {
        notification.classList.add('show');
        setTimeout(() => closeNotification(), 4000);
    }
}

function closeNotification() {
    const notification = document.getElementById('successNotification');
    if (notification) notification.classList.remove('show');
}