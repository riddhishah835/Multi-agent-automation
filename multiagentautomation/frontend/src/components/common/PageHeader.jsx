export default function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-header">
      <section>
        <h1>{title}</h1>
        {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
      </section>
      {actions && <section className="page-header__actions">{actions}</section>}
    </header>
  );
}
