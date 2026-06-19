document.addEventListener('DOMContentLoaded', () => {
    
    // --- Auto-Login (حفظ تسجيل الدخول) ---
    // الكود ده بيبص لو التوكن موجود، يوجهك لصفحتك فوراً بدون ما يطلب لوجين تاني
    const savedToken = localStorage.getItem('token');
    const savedRole = localStorage.getItem('role');
    
    if (savedToken && savedRole) {
        if (savedRole === 'OWNER') window.location.replace('owner_dashboard.html');
        else if (savedRole === 'ADMIN') window.location.replace('admin_dashboard.html');
        else if (savedRole === 'DOCTOR') window.location.replace('doctor_hub.html');
        else window.location.replace('dashboard.html');
        return; // بنوقف تنفيذ باقي سكريبت اللوجين عشان إنت مسجل دخول بالفعل
    }

    // --- Configuration ---
    // التأكد من استخدام الـ Config عشان الـ API
    const API_BASE_URL = (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL) ? CONFIG.API_BASE_URL : 'http://127.0.0.1:8000';

    // --- DOM Elements ---
    const themeToggle = document.getElementById('theme-toggle');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const formLogin = document.getElementById('login-form');
    const formRegister = document.getElementById('register-form');
    const roleSelect = document.getElementById('reg-role');
    const parentFields = document.getElementById('parent-fields');
    const doctorFields = document.getElementById('doctor-fields');
    
    // Form Inputs
    const loginEmail = document.getElementById('login-email');
    const loginPassword = document.getElementById('login-password');
    const regName = document.getElementById('reg-name');
    const regEmail = document.getElementById('reg-email');
    const regPassword = document.getElementById('reg-password');
    const regConfirmPass = document.getElementById('reg-confirm-password');
    const regSpecialty = document.getElementById('reg-specialty');
    const regDocument = document.getElementById('reg-document');

    // Status Messages
    const loginError = document.getElementById('login-error');
    const regError = document.getElementById('reg-error');
    const regSuccess = document.getElementById('reg-success');

    // Email Regex Pattern
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // --- 1. Theme Toggle Logic ---
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (themeToggle) themeToggle.textContent = '☀️ Light Mode';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            if (document.body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
                themeToggle.textContent = '☀️ Light Mode';
            } else {
                localStorage.setItem('theme', 'light');
                themeToggle.textContent = '🌙 Dark Mode';
            }
        });
    }

    // --- 2. Tab Switching Logic ---
    function switchTab(showLogin) {
        // Clear old messages when switching tabs
        if(loginError) loginError.textContent = '';
        if(regError) regError.textContent = '';
        if(regSuccess) regSuccess.textContent = '';

        if (showLogin) {
            tabLogin.classList.add('active');
            tabRegister.classList.remove('active');
            formLogin.classList.add('active-form');
            formLogin.classList.remove('hidden-form');
            formRegister.classList.remove('active-form');
            formRegister.classList.add('hidden-form');
        } else {
            tabRegister.classList.add('active');
            tabLogin.classList.remove('active');
            formRegister.classList.add('active-form');
            formRegister.classList.remove('hidden-form');
            formLogin.classList.remove('active-form');
            formLogin.classList.add('hidden-form');
        }
    }

    if(tabLogin && tabRegister) {
        tabLogin.addEventListener('click', () => switchTab(true));
        tabRegister.addEventListener('click', () => switchTab(false));
    }

    // --- 3. Dynamic Registration Fields based on Role ---
    if(roleSelect) {
        roleSelect.addEventListener('change', (e) => {
            const role = e.target.value;
            if(regError) regError.textContent = '';
            if(regSuccess) regSuccess.textContent = '';

            if (role === 'DOCTOR') {
                parentFields.classList.add('hidden-element');
                doctorFields.classList.remove('hidden-element');
                regConfirmPass.removeAttribute('required');
                regDocument.setAttribute('required', 'true');
                regSpecialty.setAttribute('required', 'true');
            } else {
                parentFields.classList.remove('hidden-element');
                doctorFields.classList.add('hidden-element');
                regConfirmPass.setAttribute('required', 'true');
                regDocument.removeAttribute('required');
                regSpecialty.removeAttribute('required');
            }
        });
    }

    // --- 4. Backend Integration: Login Submission ---
    if(formLogin) {
        formLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(loginError) loginError.textContent = ''; // Reset error text

            const email = loginEmail.value.trim();
            const password = loginPassword.value;

            // Front-end Validation Check
            if (!emailRegex.test(email)) {
                if(loginError) loginError.textContent = 'Please enter a valid email address.';
                return;
            }
            if (email === "" || password === "") {
                if(regError) regError.textContent = 'All fields are mandatory!';
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE_URL}/auth/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (!response.ok) {
                    // Catch FastAPI error details (e.g., 401 Unauthorized, 403 Forbidden)
                    throw new Error(data.detail || 'Login failed. Please try again.');
                }

                // Success: Save token and role
                localStorage.setItem('token', data.access_token);
                
                // تحديد وحفظ صلاحية المستخدم (دكتور أو ولي أمر)
                const userRole = data.role ? data.role.toUpperCase() : 'PARENT';
                localStorage.setItem('role', userRole);
                localStorage.setItem('user_id', data.user_id || data.id || (data.user && data.user.id));
                
                // Temporary confirmation text before browser relocates
                if(loginError) {
                    loginError.style.color = 'var(--success-color)'; // الرسالة الخضراء
                    loginError.textContent = data.message || 'Login successful! Redirecting...';
                }
                
                // التوجيه بعد 800 مللي ثانية بناءً على الصلاحية
                setTimeout(() => {
                    if (userRole === 'OWNER') {
                        // لو اللينك مبعوت من الباك إند هنستخدمه، ولو لأ هنوجهه يدوي
                        window.location.href = data.redirect_url || 'owner_dashboard.html'; 
                    } else if (userRole === 'ADMIN') {
                        window.location.href = 'admin_dashboard.html';
                    } else if (userRole === 'DOCTOR') {
                        window.location.href = 'doctor_hub.html';
                    } else if(userRole === 'PARENT') {
                        window.location.href = 'dashboard.html';
                    }
                }, 800);

            } catch (error) {
                if(loginError) {
                    loginError.style.color = 'var(--error-color)';
                    // هنا بنخليه يتأكد لو السيرفر بعت رسالة خطأ معينة يعرضها، وإلا يعرض الرسالة العامة
                    loginError.textContent = error.message || 'Invalid email or password.';
                }
            }
        });
    }

    // --- 5. Backend Integration: Registration Submission ---
    if(formRegister) {
        formRegister.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(regError) regError.textContent = '';
            if(regSuccess) regSuccess.textContent = '';

            const role = roleSelect.value;
            const name = regName.value.trim();
            const email = regEmail.value.trim();
            const password = regPassword.value;

            // General validation checks
            if (!emailRegex.test(email)) {
                if(regError) regError.textContent = 'Please enter a valid email address.';
                return;
            }

            if (password.length < 8) {
                if(regError) regError.textContent = 'Password must be at least 8 characters long.';
                return;
            }

            // بنعمل صندوق FormData بدل الـ JSON
            const formData = new FormData();
            formData.append('role', role);
            formData.append('name', name);
            formData.append('email', email);
            formData.append('password', password);

            if (role === 'PARENT') {
                const confirmPass = regConfirmPass.value;
                if (password !== confirmPass) {
                    if(regError) regError.textContent = 'Passwords do not match.';
                    return;
                }
            } else if (role === 'DOCTOR') {
                const specialty = regSpecialty.value.trim();
                const file = regDocument.files[0];
                
                if (!specialty) {
                    if(regError) regError.textContent = 'Please specify your medical specialty.';
                    return;
                }
                if (!file) {
                    if(regError) regError.textContent = 'Please upload a verification document.';
                    return;
                }
                
                // الرفع الحقيقي: بنحط التخصص والملف نفسه جوة الصندوق
                formData.append('specialty', specialty);
                formData.append('document', file); 
            }

            try {
                const response = await fetch(`${API_BASE_URL}/auth/register`, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (!response.ok) {
                    let errorMsg = 'Registration failed.';
                    // لو الإيرور عبارة عن قائمة زي اللي FastAPI بيبعتها، هنفكها
                    if (Array.isArray(data.detail)) {
                        errorMsg = data.detail.map(err => `${err.loc[err.loc.length - 1]}: ${err.msg}`).join(' | ');
                    } else if (data.detail) {
                        errorMsg = data.detail;
                    }
                    throw new Error(errorMsg);
                }

                // Success handling
                formRegister.style.display = 'none'; // نخفي الفورم
                
                // نعرض رسالة النجاح الشيك مكان الفورم
                const authCard = document.querySelector('.auth-card');
                const successDiv = document.createElement('div');
                successDiv.style.textAlign = 'center';
                successDiv.style.padding = '40px';
                successDiv.innerHTML = `
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📬</div>
                    <h2 style="color: var(--primary); margin-bottom: 1rem;">Check Your Inbox!</h2>
                    <p style="color: var(--text-muted); font-weight: 600; margin-bottom: 2rem;">
                        Registration successful. We've sent a magic link to <strong>${email}</strong>. 
                        Please click the link in the email to verify and activate your account.
                    </p>
                    <button onclick="window.location.reload()" class="btn-primary" style="width: 100%;">Return to Login</button>
                `;
                authCard.appendChild(successDiv);

            } catch (error) {
                if(regError) regError.textContent = error.message;
            }
        });
    }

    // --- 6. Real-time Blur Validation ---

    // دالة مسؤولة عن إظهار الإيرور وتغيير لون حدود البوكس للأحمر
    function showFieldAndError(inputElement, isValid, errorMessage, errorDiv) {
        if (!isValid) {
            inputElement.style.borderColor = 'var(--error-color)';
            if(errorDiv) errorDiv.textContent = errorMessage;
        } else {
            inputElement.style.borderColor = 'var(--border-color)';
            if(errorDiv) errorDiv.textContent = '';
        }
    }

    // 1. التقييم الفوري لخانة الاسم (وقت التسجيل)
    if(regName) {
        regName.addEventListener('blur', () => {
            const isValid = regName.value.trim().length >= 2;
            showFieldAndError(regName, isValid, 'Name is mandatory and must be at least 2 characters.', regError);
        });
    }

    // 2. التقييم الفوري لخانة الإيميل (وقت التسجيل)
    if(regEmail) {
        regEmail.addEventListener('blur', () => {
            const email = regEmail.value.trim();
            let isValid = email !== "" && emailRegex.test(email);
            showFieldAndError(regEmail, isValid, 'Please enter a valid email address.', regError);
        });
    }

    // 3. التقييم الفوري لخانة الباسورد (وقت التسجيل)
    if(regPassword) {
        regPassword.addEventListener('blur', () => {
            const isValid = regPassword.value.length >= 8;
            showFieldAndError(regPassword, isValid, 'Password must be at least 8 characters long.', regError);
        });
    }

    // 4. التقييم الفوري لتأكيد الباسورد (لولي الأمر فقط)
    if(regConfirmPass) {
        regConfirmPass.addEventListener('blur', () => {
            if (roleSelect && roleSelect.value === 'PARENT') {
                const isValid = regPassword.value === regConfirmPass.value;
                showFieldAndError(regConfirmPass, isValid, 'Passwords do not match.', regError);
            }
        });
    }
});