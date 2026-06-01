# E2E Tests

## Accessibility tests (`accessibility.spec.ts`)

Runs `@axe-core/playwright` against 7 routes at WCAG 2.1 A/AA tags.

### Severity tiers

Axe-core classifies violations by `impact`:

| Level | Description | Current gate |
|---|---|---|
| `critical` | WCAG failures that make content completely inaccessible | **Blocked** |
| `serious` | Significant barriers for assistive technology users | Reported, not blocked |
| `moderate` | Noticeable issues that reduce accessibility | Reported, not blocked |
| `minor` | Low-impact deviations from best practice | Reported, not blocked |

The current threshold (`critical` only) provides a regression gate without blocking on the pre-existing `serious`/`moderate` backlog. Tightening sequence for v1.1.0 follow-ups: `critical` → `serious` → `moderate`.

### Lowering the threshold over time

To also block on `serious` violations, change `accessibility.spec.ts`:

```diff
- const critical = results.violations.filter((v) => v.impact === "critical");
+ const critical = results.violations.filter(
+   (v) => v.impact === "critical" || v.impact === "serious"
+ );
```

### Inspect violations locally

```bash
cd frontend
npx playwright test e2e/accessibility.spec.ts --reporter=list
```

For a full HTML report with violation details:

```bash
npx playwright test e2e/accessibility.spec.ts --reporter=html
npx playwright show-report
```

### WCAG mapping reference

See [axe-core rule descriptions](https://dequeuniversity.com/rules/axe/4.10) for the full mapping between axe rule IDs and WCAG success criteria.
