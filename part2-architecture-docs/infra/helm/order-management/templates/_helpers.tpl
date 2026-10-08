{{- define "oms.labels" -}}
app.kubernetes.io/part-of: order-management
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "oms.kafka-volumes" -}}
- name: kafka-ca
  secret:
    secretName: {{ .caSecret }}
- name: kafka-client
  secret:
    secretName: {{ .clientSecret }}
{{- end -}}

{{- define "oms.kafka-mounts" -}}
- name: kafka-ca
  mountPath: /var/run/kafka-ca
  readOnly: true
- name: kafka-client
  mountPath: /var/run/kafka-client
  readOnly: true
{{- end -}}

{{- define "oms.security-context" -}}
runAsNonRoot: true
runAsUser: 10001
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end -}}

{{- define "oms.health-probes" -}}
livenessProbe:
  httpGet: {path: /health/live, port: {{ .port }}}
  initialDelaySeconds: 10
  periodSeconds: 10
readinessProbe:
  httpGet: {path: /health/ready, port: {{ .port }}}
  initialDelaySeconds: 5
  periodSeconds: 5
startupProbe:
  httpGet: {path: /health/ready, port: {{ .port }}}
  failureThreshold: 60
  periodSeconds: 5
{{- end -}}

{{- define "oms.cloud-sql-proxy" -}}
- name: cloud-sql-proxy
  image: {{ .Values.cloudSqlProxy.image | quote }}
  restartPolicy: Always
  args:
    - --private-ip
    - --auto-iam-authn
    - --structured-logs
    - --health-check
    - --http-address=0.0.0.0
    - --port=5432
    - {{ .Values.writer.sqlConnectionName | quote }}
  securityContext:
    {{- include "oms.security-context" . | nindent 4 }}
  resources:
    requests: {cpu: 100m, memory: 128Mi}
    limits: {cpu: 500m, memory: 256Mi}
  startupProbe:
    httpGet: {path: /startup, port: 9090}
    failureThreshold: 30
    periodSeconds: 2
  livenessProbe:
    httpGet: {path: /liveness, port: 9090}
    periodSeconds: 10
{{- end -}}
