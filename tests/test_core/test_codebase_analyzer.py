import os
import tempfile

from core.codebase_analyzer import analyze_codebase, format_context
from core.stack_detector import StackInfo, detect_stack


def _make_project(tmp, files: dict[str, str]):
    for path, content in files.items():
        full = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)


class TestCodebaseAnalyzer:
    def test_nextjs_project(self, tmp_path):
        _make_project(str(tmp_path), {
            "package.json": '{"dependencies":{"next":"14.0.0","react":"18.0.0"},"devDependencies":{"vitest":"1.0.0"}}',
            "tsconfig.json": "{}",
            "app/layout.tsx": "export default function RootLayout({children}) { return <html>{children}</html> }",
            "app/page.tsx": "export default function Home() { return <h1>Hello</h1> }",
            "app/api/users/route.ts": "export async function GET() { return Response.json([]) }",
            "prisma/schema.prisma": "model User {\n  id Int @id\n  name String\n  email String\n  posts Post[]\n}\n\nmodel Post {\n  id Int @id\n  title String\n  authorId Int\n}",
            "README.md": "# My E-commerce App\nA Next.js app for selling widgets.",
        })

        stack = detect_stack(str(tmp_path))
        assert stack.language == "typescript"
        assert stack.framework == "nextjs"

        ctx = analyze_codebase(str(tmp_path), stack)

        assert ctx.readme.startswith("# My E-commerce App")
        assert any("layout" in ep["path"] for ep in ctx.entry_points)
        assert any(m["name"] == "User" for m in ctx.models)
        assert any(m["name"] == "Post" for m in ctx.models)

        user_model = next(m for m in ctx.models if m["name"] == "User")
        assert "name" in user_model["fields"]
        assert "email" in user_model["fields"]

        assert any("users" in r["path"] for r in ctx.routes)

        formatted = format_context(ctx)
        assert "README" in formatted
        assert "User" in formatted
        assert "prisma" in formatted.lower()

    def test_django_project(self, tmp_path):
        _make_project(str(tmp_path), {
            "requirements.txt": "django==5.0\npytest\n",
            "manage.py": "#!/usr/bin/env python\nimport django\n",
            "app/models.py": (
                "from django.db import models\n\n"
                "class Product(models.Model):\n"
                "    name = models.CharField(max_length=200)\n"
                "    price = models.DecimalField(max_digits=10, decimal_places=2)\n"
            ),
            "app/views.py": (
                "from django.http import JsonResponse\n\n"
                "def product_list(request):\n"
                "    return JsonResponse([], safe=False)\n"
            ),
            "config/urls.py": (
                "from django.urls import path\n"
                "from app.views import product_list\n\n"
                "urlpatterns = [\n"
                "    path('api/products/', product_list),\n"
                "]\n"
            ),
        })

        stack = detect_stack(str(tmp_path))
        assert stack.language == "python"
        assert stack.framework == "django"

        ctx = analyze_codebase(str(tmp_path), stack)

        assert any(m["name"] == "Product" for m in ctx.models)
        product = next(m for m in ctx.models if m["name"] == "Product")
        assert "name" in product["fields"]
        assert "price" in product["fields"]

        assert any("products" in r["path"] for r in ctx.routes)

    def test_express_project(self, tmp_path):
        _make_project(str(tmp_path), {
            "package.json": '{"dependencies":{"express":"4.18.0"}}',
            "src/index.js": (
                "const express = require('express');\n"
                "const app = express();\n"
                "app.get('/api/users', (req, res) => res.json([]));\n"
                "app.post('/api/users', (req, res) => res.status(201).json({}));\n"
                "app.get('/api/products', (req, res) => res.json([]));\n"
            ),
        })

        stack = detect_stack(str(tmp_path))
        assert stack.framework == "express"

        ctx = analyze_codebase(str(tmp_path), stack)
        assert any("/api/users" in r["path"] for r in ctx.routes)
        assert any("/api/products" in r["path"] for r in ctx.routes)

    def test_laravel_project(self, tmp_path):
        _make_project(str(tmp_path), {
            "composer.json": '{"require":{"laravel/framework":"^11.0"}}',
            "artisan": "#!/usr/bin/env php\n",
            "routes/api.php": (
                "<?php\n"
                "Route::get('/orders', [OrderController::class, 'index']);\n"
                "Route::post('/orders', [OrderController::class, 'store']);\n"
            ),
            "app/Models/Order.php": (
                "<?php\nnamespace App\\Models;\n"
                "class Order extends Model {\n"
                "    protected $fillable = ['total', 'status', 'user_id'];\n"
                "}\n"
            ),
        })

        stack = detect_stack(str(tmp_path))
        assert stack.framework == "laravel"

        ctx = analyze_codebase(str(tmp_path), stack)
        assert any(m["name"] == "Order" for m in ctx.models)
        assert any("/orders" in r["path"] for r in ctx.routes)

    def test_empty_project(self, tmp_path):
        stack = StackInfo(language="unknown")
        ctx = analyze_codebase(str(tmp_path), stack)
        assert ctx.models == []
        assert ctx.routes == []
        formatted = format_context(ctx)
        assert "Stack:" in formatted

    def test_format_includes_key_sections(self, tmp_path):
        _make_project(str(tmp_path), {
            "package.json": '{"dependencies":{"next":"14.0.0"}}',
            "tsconfig.json": "{}",
            "README.md": "# Test Project",
            ".env.example": "DATABASE_URL=postgres://...",
        })

        stack = detect_stack(str(tmp_path))
        ctx = analyze_codebase(str(tmp_path), stack)
        formatted = format_context(ctx)

        assert "README" in formatted
        assert "Directory Structure" in formatted
        assert "Configuration" in formatted

    def test_rails_project(self, tmp_path):
        _make_project(str(tmp_path), {
            "Gemfile": "gem 'rails'\ngem 'rspec'\n",
            "config/routes.rb": (
                "Rails.application.routes.draw do\n"
                "  resources :articles\n"
                "  get '/health', to: 'health#check'\n"
                "end\n"
            ),
            "app/models/article.rb": (
                "class Article < ApplicationRecord\n"
                "  has_many :comments\n"
                "end\n"
            ),
            "config/application.rb": "module MyApp; class Application < Rails::Application; end; end",
        })

        stack = detect_stack(str(tmp_path))
        assert stack.framework == "rails"

        ctx = analyze_codebase(str(tmp_path), stack)
        assert any(m["name"] == "Article" for m in ctx.models)
        assert any("/articles" in r["path"] for r in ctx.routes)
