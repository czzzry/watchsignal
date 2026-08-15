import { LoginForm } from "./login-form";
import styles from "./login.module.css";

export default function LoginPage() {
  return (
    <main className={styles.loginShell} data-watchsignal-login>
      <LoginForm />
    </main>
  );
}
