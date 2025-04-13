// Supabase Client Initialization (from environment variables passed via Flask/HTML)
// It's safer to expose these via a dedicated endpoint or embedded in HTML by Flask
// For now, we assume SUPABASE_URL and SUPABASE_KEY are available globally
// A better approach is needed for production.

// Example: Fetch from backend endpoint (requires a new Flask route)
/*
let supabaseClient;
let initializeAuthAttempted = false; // Flag to prevent multiple initializations

async function initializeSupabaseClient() {
    if (supabaseClient || initializeAuthAttempted) return; // Already initialized or attempt in progress
    initializeAuthAttempted = true; // Mark attempt
    console.log('Fetching Supabase config from /config...');
    try {
        const response = await fetch('/config');
        if (!response.ok) {
            throw new Error(`Failed to fetch config: ${response.statusText}`);
        }
        const config = await response.json();

        if (!config.supabaseUrl || !config.supabaseKey) {
            console.error('Supabase config not found or incomplete in response from /config.');
            // Display error to user on the page?
            return;
        }

        console.log('Supabase config received, initializing client...');
        supabaseClient = supabase.createClient(config.supabaseUrl, config.supabaseKey);
        console.log('Supabase client initialized successfully via /config.');
        initializeAuthListeners(); // Initialize listeners AFTER client is ready
        checkInitialAuthState(); // Check initial state AFTER client is ready

    } catch (error) {
        console.error('Error initializing Supabase client:', error);
        // Display a more prominent error on the page?
        const body = document.querySelector('body');
        if (body) {
             const errorDiv = document.createElement('div');
             errorDiv.textContent = 'アプリケーション設定の読み込みに失敗しました。管理者に連絡してください。';
             errorDiv.style.color = 'red';
             errorDiv.style.backgroundColor = '#fdd';
             errorDiv.style.padding = '10px';
             errorDiv.style.textAlign = 'center';
             errorDiv.style.fontWeight = 'bold';
             body.insertBefore(errorDiv, body.firstChild);
        }
    }
}

function initializeAuthListeners() {
    if (!supabaseClient) return;
    console.log('Initializing auth state listener...');
    supabaseClient.auth.onAuthStateChange((event, session) => {
        console.log('Auth event:', event, 'Session:', session);
        const user = session?.user;

        // If user is logged in and on login/signup page, redirect to main page
        if (user && (window.location.pathname === '/login' || window.location.pathname === '/signup')) {
            console.log('User logged in, redirecting from auth page.');
            window.location.href = '/'; // Redirect to home/dashboard
        }
        // If user is not logged in and on a protected page, redirect to login
        else if (!user && !['/login', '/signup'].includes(window.location.pathname)) {
            console.log('User not logged in, redirecting to login.');
            // Check if we are already on the login page to avoid redirect loop
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        // If user is logged in, update UI elements (e.g., show logout button)
        else if (user) {
            console.log('User is logged in:', user.email);
            updateUIForLoggedInUser(user);
        }
        // If user is logged out, update UI elements (e.g., show login button)
        else {
             console.log('User is logged out.');
            updateUIForLoggedOutUser();
        }
    });
}

function checkInitialAuthState() {
    if (!supabaseClient) return;
    console.log('Checking initial auth state...');
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (session?.user) {
        updateUIForLoggedInUser(session.user);
    } else {
        updateUIForLoggedOutUser();
        // Redirect if necessary and not on auth pages
        if (!['/login', '/signup'].includes(window.location.pathname)) {
             if (window.location.pathname !== '/login') { // Prevent loop
                console.log('Initial load: No session, redirecting to login.');
                // window.location.href = '/login'; // Let onAuthStateChange handle this to avoid race conditions
            }
        }
    }
}
*/

// --- Temporary/Insecure approach for local dev ---
// Replace these with your actual Supabase URL and Anon Key during development
// **NEVER commit these directly into your code**
// Use environment variables or a config endpoint in production.
// Comment out or remove direct initialization
// const SUPABASE_URL = 'https://ftcljbccnnmdmkmeesjv.supabase.co'; // Replaced with actual URL
// const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ0Y2xqYmNjbm5tZG1rbWVlc2p2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQzNDU5ODYsImV4cCI6MjA1OTkyMTk4Nn0.pf-m-ot-1do-t5uGWJy_CoT-itL71ck31EyRXl6Q_FE'; // Replaced with actual Anon Key
 
// Removed the warning check as placeholders are replaced.
 
// Comment out or remove direct initialization
// const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
// console.log('Supabase client initialized in auth.js');
 
// --- Auth State Change Listener ---
// This runs when the script loads and whenever the auth state changes
// Define listener function separately, call after client init
function initializeAuthListeners() {
    if (!supabaseClient) return;
    console.log('Initializing auth state listener...');
    supabaseClient.auth.onAuthStateChange((event, session) => {
        console.log('Auth event:', event, 'Session:', session);
        const user = session?.user;

        // If user is logged in and on login/signup page, redirect to main page
        if (user && (window.location.pathname === '/login' || window.location.pathname === '/signup')) {
            console.log('User logged in, redirecting from auth page.');
            window.location.href = '/'; // Redirect to home/dashboard
        }
        // If user is not logged in and on a protected page, redirect to login
        else if (!user && !['/login', '/signup'].includes(window.location.pathname)) {
            console.log('User not logged in, redirecting to login.');
            // Check if we are already on the login page to avoid redirect loop
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        // If user is logged in, update UI elements (e.g., show logout button)
        else if (user) {
            console.log('User is logged in:', user.email);
            updateUIForLoggedInUser(user);
        }
        // If user is logged out, update UI elements (e.g., show login button)
        else {
             console.log('User is logged out.');
            updateUIForLoggedOutUser();
        }
    });
} // End of initializeAuthListeners

// --- UI Update Functions ---
function updateUIForLoggedInUser(user) {
    // Example: Find a placeholder element and display user info/logout button
    const userInfoElement = document.getElementById('user-info');
    const logoutButton = document.getElementById('logout-button');

    if (userInfoElement) {
        userInfoElement.textContent = `ログイン中: ${user.email}`; // Display user email
        userInfoElement.style.display = 'block';
    }
    if (logoutButton) {
        logoutButton.style.display = 'inline-block'; // Show logout button
        logoutButton.onclick = handleLogout; // Assign logout handler
    }
     // Hide login/signup links if they exist on the page
    const loginLink = document.getElementById('login-link');
    const signupLink = document.getElementById('signup-link');
    if(loginLink) loginLink.style.display = 'none';
    if(signupLink) signupLink.style.display = 'none';
}

function updateUIForLoggedOutUser() {
    const userInfoElement = document.getElementById('user-info');
    const logoutButton = document.getElementById('logout-button');
     const loginLink = document.getElementById('login-link');
    const signupLink = document.getElementById('signup-link');

    if (userInfoElement) userInfoElement.style.display = 'none';
    if (logoutButton) logoutButton.style.display = 'none';
    if(loginLink) loginLink.style.display = 'inline-block'; // Show login link
    if(signupLink) signupLink.style.display = 'inline-block'; // Show signup link

}

// --- Form Handlers ---
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const errorMessageDiv = document.getElementById('error-message');
const successMessageDiv = document.getElementById('success-message');

if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!supabaseClient) {
            console.error('Supabase client not initialized yet.');
            displayMessage(errorMessageDiv, '認証サービスの準備中です。少し待ってから再試行してください。');
            return;
        }
        clearMessages();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        console.log('Attempting login for:', email);
        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email: email,
            password: password,
        });

        if (error) {
            console.error('Login error:', error);
            displayMessage(errorMessageDiv, `ログインエラー: ${error.message}`);
        } else {
            console.log('Login successful, session:', data.session);
            // onAuthStateChange will handle redirect
            // displayMessage(successMessageDiv, 'ログインに成功しました。リダイレクトします...');
            // setTimeout(() => window.location.href = '/', 1000); // Redirect handled by listener
        }
    });
}

if (signupForm) {
    signupForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!supabaseClient) {
            console.error('Supabase client not initialized yet.');
            displayMessage(errorMessageDiv, '認証サービスの準備中です。少し待ってから再試行してください。');
            return;
        }
        clearMessages();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        // Optional: Add password confirmation check here

        console.log('Attempting signup for:', email);
        const { data, error } = await supabaseClient.auth.signUp({
            email: email,
            password: password,
            // Options for email confirmation, user metadata, etc. can be added here
            // options: {
            //   emailRedirectTo: 'http://localhost:5001/', // Where to redirect after email confirmation
            // }
        });

        if (error) {
            console.error('Signup error:', error);
            displayMessage(errorMessageDiv, `登録エラー: ${error.message}`);
        } else {
             console.log('Signup successful, user:', data.user);
             // Check if email confirmation is required
            if (data.user && data.user.identities && data.user.identities.length === 0) {
                 displayMessage(successMessageDiv, '確認メールを送信しました。メールを確認して登録を完了してください。');
             } else if (data.session) {
                // User might be auto-confirmed or already logged in (e.g., if email confirmation is disabled)
                displayMessage(successMessageDiv, '登録が成功しました。');
                 // onAuthStateChange will handle redirect if session is active
             } else {
                 // Likely means confirmation email sent
                 displayMessage(successMessageDiv, '確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。');
            }
            // Optionally clear the form
            signupForm.reset();
        }
    });
}

// --- Logout Handler ---
async function handleLogout() {
    if (!supabaseClient) {
        console.error('Supabase client not initialized yet.');
        return; // Or show an error
    }
    console.log('Attempting logout...');
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
        console.error('Logout error:', error);
        // Display error to user if needed
    } else {
        console.log('Logout successful.');
        // onAuthStateChange will handle redirect to login page
        // window.location.href = '/login'; // Redirect handled by listener
    }
}

// Helper to display messages
function displayMessage(element, message) {
    if (element) {
        element.textContent = message;
        element.style.display = 'block'; // Make sure it's visible
    }
}

// Helper to clear messages
function clearMessages() {
    if (errorMessageDiv) errorMessageDiv.textContent = '';
    if (successMessageDiv) successMessageDiv.textContent = '';
}


// --- API Fetch Wrapper (Example) ---
// Use this function to make authenticated requests to your Flask backend
async function fetchAuthenticatedApi(url, options = {}) {
    if (!supabaseClient) {
        console.error('fetchAuthenticatedApi called before Supabase client initialization.');
        // Attempt to initialize if not already attempted
        if (!initializeAuthAttempted) {
            await initializeSupabaseClient();
        }
        // If still not initialized, throw error
        if (!supabaseClient) {
             throw new Error('Supabase client failed to initialize');
        }
        // Otherwise, continue now that the client should be ready
    }

    const { data: { session }, error: sessionError } = await supabaseClient.auth.getSession();

    if (sessionError || !session) {
        console.error('Error getting session or no active session:', sessionError);
        // Handle error appropriately, maybe redirect to login
        window.location.href = '/login';
        throw new Error('User not authenticated');
    }

    const token = session.access_token;

    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json' // Assume JSON unless specified otherwise
    };

    console.log(`Fetching ${url} with token.`);
    try {
        const response = await fetch(url, { ...options, headers });

        if (!response.ok) {
            // Attempt to read error response from backend
            let errorData;
            try {
                 errorData = await response.json();
            } catch (e) {
                 errorData = { error: `HTTP error ${response.status}` };
            }
            console.error(`API error ${response.status}:`, errorData);
            throw new Error(errorData.error || `Request failed with status ${response.status}`);
        }

        // Handle responses with no content
        if (response.status === 204 || response.headers.get("content-length") === "0") {
             return null; // Or {} or whatever makes sense for no content
        }

        return await response.json(); // Assume JSON response
    } catch (error) {
        console.error(`Fetch error for ${url}:`, error);
        throw error; // Re-throw the error to be caught by the caller
    }
}

// Example usage of fetchAuthenticatedApi (to be used in chat.js, manage.js etc.)
/*
async function getDocuments() {
    try {
        const documents = await fetchAuthenticatedApi('/api/document/list');
        console.log('Fetched documents:', documents);
        // Update UI with documents
    } catch (error) {
        console.error('Failed to fetch documents:', error);
        // Display error to user
    }
}
*/

// --- Initial UI Update on Load ---
// Modify initial check to wait for client initialization
async function checkInitialAuthState() {
    if (!supabaseClient) return;
    console.log('Checking initial auth state...');
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (session?.user) {
        updateUIForLoggedInUser(session.user);
    } else {
        updateUIForLoggedOutUser();
        // Redirect if necessary and not on auth pages
        if (!['/login', '/signup'].includes(window.location.pathname)) {
             if (window.location.pathname !== '/login') { // Prevent loop
                console.log('Initial load: No session, redirecting to login.');
                // window.location.href = '/login'; // Let onAuthStateChange handle this to avoid race conditions
            }
        }
    }
}

// --- Start Initialization ---
// Call the function to fetch config and initialize the client when the script loads
initializeSupabaseClient(); 