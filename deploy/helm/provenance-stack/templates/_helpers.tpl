{{- define "provenance-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "provenance-stack.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "provenance-stack.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "provenance-stack.labels" -}}
app.kubernetes.io/name: {{ include "provenance-stack.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "provenance-stack.databaseUrl" -}}
{{- if .Values.externalDatabase.enabled -}}
{{- .Values.externalDatabase.url -}}
{{- else -}}
{{- $name := include "provenance-stack.fullname" . -}}
{{- printf "postgresql+asyncpg://%s:%s@%s-postgres:%d/%s" .Values.postgres.auth.username .Values.postgres.auth.password $name (.Values.postgres.service.port | int) .Values.postgres.auth.database -}}
{{- end -}}
{{- end -}}

{{- define "provenance-stack.imageRef" -}}
{{- $repo := required "image.repository is required" .repository -}}
{{- $digest := default "" .digest -}}
{{- if $digest -}}
{{- printf "%s@%s" $repo $digest -}}
{{- else -}}
{{- $tag := default "latest" .tag -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end -}}
