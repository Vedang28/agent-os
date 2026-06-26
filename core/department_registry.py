from core.graph import register_department_graph
from infra.telemetry import get_logger

logger = get_logger("core.department_registry")

_PIPELINE_KEYWORDS = [
    "build project", "create project", "new project", "prd", "product requirement",
    "build app", "create app", "new app", "full stack", "end to end", "from scratch",
    "build me", "create me", "make me", "implement this", "build this",
    "scaffold project", "start project", "init project", "bootstrap",
]

_DEPARTMENT_CONFIG = {
    "engineering": {
        "module": "agents.departments.engineering.graph",
        "builder": "build_engineering_graph",
        "keywords": ["build", "create", "design", "implement", "code", "api", "engineer", "develop", "program", "scaffold"],
    },
    "intelligence": {
        "module": "agents.departments.intelligence.graph",
        "builder": "build_intelligence_graph",
        "keywords": ["briefing", "intelligence", "research", "trends", "news", "analyze", "investigate", "report"],
    },
    "backend": {
        "module": "agents.departments.backend.graph",
        "builder": "build_backend_graph",
        "keywords": ["backend", "endpoint", "controller", "route", "rest", "graphql", "middleware", "server"],
    },
    "database": {
        "module": "agents.departments.database.graph",
        "builder": "build_database_graph",
        "keywords": ["database", "schema", "migration", "sql", "query", "table", "index", "orm", "postgres", "mysql", "mongo"],
    },
    "auth": {
        "module": "agents.departments.auth.graph",
        "builder": "build_auth_graph",
        "keywords": ["auth", "login", "signup", "jwt", "oauth", "session", "permission", "rbac", "token", "sso", "mfa"],
    },
    "api_gateway": {
        "module": "agents.departments.api_gateway.graph",
        "builder": "build_api_gateway_graph",
        "keywords": ["gateway", "rate limit", "throttle", "cache", "cdn", "proxy", "load balance"],
    },
    "frontend": {
        "module": "agents.departments.frontend.graph",
        "builder": "build_frontend_graph",
        "keywords": ["frontend", "react", "next", "vue", "component", "ui", "page", "layout", "form", "button"],
    },
    "frontend_design": {
        "module": "agents.departments.frontend_design.graph",
        "builder": "build_frontend_design_graph",
        "keywords": ["design", "ux", "wireframe", "prototype", "theme", "style", "color", "typography", "dark mode"],
    },
    "graphics": {
        "module": "agents.departments.graphics.graph",
        "builder": "build_graphics_graph",
        "keywords": ["graphic", "icon", "illustration", "logo", "brand", "asset", "image", "svg", "favicon"],
    },
    "testing": {
        "module": "agents.departments.testing.graph",
        "builder": "build_testing_graph",
        "keywords": ["test", "pytest", "jest", "coverage", "unit test", "integration test", "e2e", "spec"],
    },
    "ui_testing": {
        "module": "agents.departments.ui_testing.graph",
        "builder": "build_ui_testing_graph",
        "keywords": ["playwright", "visual test", "screenshot", "visual regression", "browser test", "ui test"],
    },
    "devops": {
        "module": "agents.departments.devops.graph",
        "builder": "build_devops_graph",
        "keywords": ["ci", "cd", "pipeline", "deploy", "release", "docker", "container", "github actions", "gitlab"],
    },
    "cloud": {
        "module": "agents.departments.cloud.graph",
        "builder": "build_cloud_graph",
        "keywords": ["cloud", "aws", "gcp", "azure", "terraform", "infrastructure", "vpc", "kubernetes", "k8s"],
    },
    "observability": {
        "module": "agents.departments.observability.graph",
        "builder": "build_observability_graph",
        "keywords": ["monitor", "observability", "alert", "logging", "tracing", "metrics", "prometheus", "grafana", "pagerduty"],
    },
    "ai_agent": {
        "module": "agents.departments.ai_agent.graph",
        "builder": "build_ai_agent_graph",
        "keywords": ["prompt", "llm", "ai agent", "function calling", "tool use", "model", "embedding", "rag"],
    },
    "ml": {
        "module": "agents.departments.ml.graph",
        "builder": "build_ml_graph",
        "keywords": ["ml", "machine learning", "training", "fine-tune", "dataset", "model training", "embedding pipeline"],
    },
    "marketing": {
        "module": "agents.departments.marketing.graph",
        "builder": "build_marketing_graph",
        "keywords": ["marketing", "campaign", "content", "social media", "email marketing", "copywriting", "ad"],
    },
    "lead_gen": {
        "module": "agents.departments.lead_gen.graph",
        "builder": "build_lead_gen_graph",
        "keywords": ["lead", "prospect", "outbound", "icp", "qualification", "crm", "pipeline"],
    },
    "seo": {
        "module": "agents.departments.seo.graph",
        "builder": "build_seo_graph",
        "keywords": ["seo", "keyword", "search engine", "ranking", "meta tag", "sitemap", "backlink", "serp"],
    },
    "sdr": {
        "module": "agents.departments.sdr.graph",
        "builder": "build_sdr_graph",
        "keywords": ["sales", "outreach", "cold email", "sequence", "follow-up", "deal", "close"],
    },
    "support": {
        "module": "agents.departments.support.graph",
        "builder": "build_support_graph",
        "keywords": ["support", "ticket", "help", "troubleshoot", "issue", "customer", "bug report"],
    },
    "finance": {
        "module": "agents.departments.finance.graph",
        "builder": "build_finance_graph",
        "keywords": ["finance", "revenue", "expense", "budget", "invoice", "accounting", "mrr", "runway", "burn rate"],
    },
    "screen": {
        "module": "agents.departments.screen.graph",
        "builder": "build_screen_graph",
        "keywords": ["screenshot", "screen capture", "ui analysis", "screen read", "visual inspect"],
    },
    "video": {
        "module": "agents.departments.video.graph",
        "builder": "build_video_graph",
        "keywords": ["video", "clip", "scene", "transcript", "subtitle", "footage"],
    },
    "document": {
        "module": "agents.departments.document.graph",
        "builder": "build_document_graph",
        "keywords": ["document", "pdf", "extract", "ocr", "spreadsheet", "form", "table extraction"],
    },
    "memory": {
        "module": "agents.departments.memory.graph",
        "builder": "build_memory_graph",
        "keywords": ["session", "decision", "adr", "log", "remember", "recall", "history"],
    },
    "code_review": {
        "module": "agents.departments.code_review.graph",
        "builder": "build_code_review_graph",
        "keywords": ["review", "code review", "pr review", "pull request", "diff", "changeset"],
    },
    "dev_testing": {
        "module": "agents.departments.dev_testing.graph",
        "builder": "build_dev_testing_graph",
        "keywords": ["write test", "add test", "test plan", "test strategy", "missing test"],
    },
    "security_dev": {
        "module": "agents.departments.security_dev.graph",
        "builder": "build_security_dev_graph",
        "keywords": ["security", "vulnerability", "injection", "xss", "csrf", "owasp", "pentest", "audit"],
    },
    "bug_triage": {
        "module": "agents.departments.bug_triage.graph",
        "builder": "build_bug_triage_graph",
        "keywords": ["bug", "triage", "reproduce", "crash", "error", "debug", "fix"],
    },
    "dependency": {
        "module": "agents.departments.dependency.graph",
        "builder": "build_dependency_graph",
        "keywords": ["dependency", "package", "npm", "pip", "upgrade", "cve", "outdated", "license"],
    },
    "documentation": {
        "module": "agents.departments.documentation.graph",
        "builder": "build_documentation_graph",
        "keywords": ["documentation", "readme", "docs", "jsdoc", "docstring", "api docs", "tutorial"],
    },
    "performance": {
        "module": "agents.departments.performance.graph",
        "builder": "build_performance_graph",
        "keywords": ["performance", "optimize", "slow", "latency", "memory leak", "profil", "benchmark", "bundle size"],
    },
    "devops_ci": {
        "module": "agents.departments.devops_ci.graph",
        "builder": "build_devops_ci_graph",
        "keywords": ["ci fix", "flaky test", "build time", "pipeline fix", "ci monitor", "build fail"],
    },
}


def register_all_departments(librarian=None, obsidian=None, tool_registry=None):
    import inspect

    kwargs_full = {"librarian": librarian, "obsidian": obsidian, "tool_registry": tool_registry}
    registered = []
    for name, config in _DEPARTMENT_CONFIG.items():
        try:
            module = __import__(config["module"], fromlist=[config["builder"]])
            builder = getattr(module, config["builder"])
            sig = inspect.signature(builder)
            kwargs = {k: v for k, v in kwargs_full.items() if k in sig.parameters}
            graph = builder(**kwargs)
            register_department_graph(name, graph, keywords=config["keywords"])
            registered.append(name)
        except Exception as e:
            logger.error("failed to register department=%s: %s", name, e)
    try:
        from core.pipeline import build_pipeline_graph
        pipeline = build_pipeline_graph(
            librarian=librarian, obsidian=obsidian, tool_registry=tool_registry
        )
        register_department_graph("pipeline", pipeline, keywords=_PIPELINE_KEYWORDS)
        registered.append("pipeline")
        logger.info("registered pipeline (9-stage code pipeline)")
    except Exception as e:
        logger.error("failed to register pipeline: %s", e)

    logger.info("registered %d/%d departments + pipeline", len(registered), len(_DEPARTMENT_CONFIG) + 1)
    return registered
