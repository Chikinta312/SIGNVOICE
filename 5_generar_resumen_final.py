"""
generar_resumen_final.py — Consolidación de pruebas completadas
===============================================================
Ejecuta este script después de completar todas las pruebas de usuarios
para generar un resumen final consolidado con estadísticas globales.

Uso:
    python generar_resumen_final.py
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

PRUEBAS_DIR = "PRUEBAS"


def generar_resumen_final():
    """Genera un resumen consolidado de todas las pruebas."""
    if not os.path.exists(PRUEBAS_DIR):
        print("❌ La carpeta 'PRUEBAS' no existe. Asegúrate de haber ejecutado pruebas.")
        return
    
    carpeta_resumen = os.path.join(PRUEBAS_DIR, "RESUMEN_FINAL")
    os.makedirs(carpeta_resumen, exist_ok=True)
    
    print("\n" + "="*70)
    print("  GENERANDO RESUMEN FINAL DE PRUEBAS DE SIGNVOICE")
    print("="*70)
    
    # Recopilar datos de todos los usuarios
    resumen_usuarios = []
    todos_datos_detallados = []
    resumen_por_letra_global = {}
    
    usuarios_procesados = 0
    
    for usuario_dir in sorted(os.listdir(PRUEBAS_DIR)):
        if usuario_dir.startswith("USER"):
            num_usuario = int(usuario_dir.replace("USER", ""))
            carpeta_usuario = os.path.join(PRUEBAS_DIR, usuario_dir)
            
            # Buscar archivo Excel
            archivo_excel = os.path.join(carpeta_usuario, f"usuario_{num_usuario}_datos.xlsx")
            if os.path.exists(archivo_excel):
                try:
                    df_metricas = pd.read_excel(archivo_excel, sheet_name='Metricas Generales')
                    df_resumen_letra = pd.read_excel(archivo_excel, sheet_name='Resumen por Letra')
                    df_detallados = pd.read_excel(archivo_excel, sheet_name='Datos Detallados')
                    
                    resumen_usuarios.append(df_metricas.iloc[0].to_dict())
                    todos_datos_detallados.append(df_detallados)
                    
                    # Agregar al resumen por letra
                    for _, fila in df_resumen_letra.iterrows():
                        letra = fila['Letra']
                        if letra not in resumen_por_letra_global:
                            resumen_por_letra_global[letra] = {
                                'reconocimientos': 0,
                                'confianzas': [],
                                'latencias': [],
                            }
                        resumen_por_letra_global[letra]['reconocimientos'] += fila['Reconocimientos']
                        resumen_por_letra_global[letra]['confianzas'].append(fila['Confianza Promedio'])
                        resumen_por_letra_global[letra]['latencias'].append(fila['Latencia Promedio (ms)'])
                    
                    print(f"  ✓ Datos de USER{num_usuario:2d} recopilados ({len(df_detallados)} reconocimientos)")
                    usuarios_procesados += 1
                except Exception as e:
                    print(f"  ⚠ Error al leer USER{num_usuario}: {e}")
    
    if not resumen_usuarios:
        print("  ❌ No hay datos de usuarios para resumir.")
        return
    
    print(f"\n  Total de usuarios procesados: {usuarios_procesados}\n")
    
    # Crear DataFrames de resumen
    df_resumen_usuarios = pd.DataFrame(resumen_usuarios)
    df_todos_datos = pd.concat(todos_datos_detallados, ignore_index=True) if todos_datos_detallados else pd.DataFrame()
    
    # Crear resumen por letra
    resumen_letras_data = []
    for letra in sorted(resumen_por_letra_global.keys()):
        datos = resumen_por_letra_global[letra]
        resumen_letras_data.append({
            'Letra': letra,
            'Total Reconocimientos': datos['reconocimientos'],
            'Confianza Promedio': np.mean(datos['confianzas']) if datos['confianzas'] else 0,
            'Confianza Min': np.min(datos['confianzas']) if datos['confianzas'] else 0,
            'Confianza Max': np.max(datos['confianzas']) if datos['confianzas'] else 0,
            'Latencia Promedio (ms)': np.mean(datos['latencias']) if datos['latencias'] else 0,
            'Latencia Min (ms)': np.min(datos['latencias']) if datos['latencias'] else 0,
            'Latencia Max (ms)': np.max(datos['latencias']) if datos['latencias'] else 0,
        })
    df_resumen_letras = pd.DataFrame(resumen_letras_data)
    
    # Calcular estadísticas generales
    if len(df_todos_datos) > 0:
        stats_generales = {
            'Métrica': [
                'Total Usuarios',
                'Total Reconocimientos',
                'Letras Únicas Reconocidas',
                'Promedio Reconocimientos por Usuario',
                '',
                'Confianza Promedio Global',
                'Confianza Mínima',
                'Confianza Máxima',
                'Desv. Estándar Confianza',
                'Confianza Percentil 25',
                'Confianza Percentil 50 (Mediana)',
                'Confianza Percentil 75',
                '',
                'Latencia Promedio (ms)',
                'Latencia Mínima (ms)',
                'Latencia Máxima (ms)',
                'Desv. Estándar Latencia (ms)',
                'Latencia Percentil 25 (ms)',
                'Latencia Percentil 50 (ms)',
                'Latencia Percentil 75 (ms)',
                '',
                'Tiempo Total Pruebas (minutos)',
                'Tiempo Promedio por Usuario (minutos)',
            ],
            'Valor': [
                len(df_resumen_usuarios),
                int(df_resumen_usuarios['total_reconocimientos'].sum()),
                len(resumen_por_letra_global),
                f"{df_resumen_usuarios['total_reconocimientos'].mean():.1f}",
                '',
                f"{df_todos_datos['confianza'].mean():.4f}",
                f"{df_todos_datos['confianza'].min():.4f}",
                f"{df_todos_datos['confianza'].max():.4f}",
                f"{df_todos_datos['confianza'].std():.4f}",
                f"{df_todos_datos['confianza'].quantile(0.25):.4f}",
                f"{df_todos_datos['confianza'].quantile(0.50):.4f}",
                f"{df_todos_datos['confianza'].quantile(0.75):.4f}",
                '',
                f"{df_todos_datos['latencia_ms'].mean():.2f}",
                f"{df_todos_datos['latencia_ms'].min():.2f}",
                f"{df_todos_datos['latencia_ms'].max():.2f}",
                f"{df_todos_datos['latencia_ms'].std():.2f}",
                f"{df_todos_datos['latencia_ms'].quantile(0.25):.2f}",
                f"{df_todos_datos['latencia_ms'].quantile(0.50):.2f}",
                f"{df_todos_datos['latencia_ms'].quantile(0.75):.2f}",
                '',
                f"{df_resumen_usuarios['tiempo_prueba_segundos'].sum() / 60:.1f}",
                f"{df_resumen_usuarios['tiempo_prueba_segundos'].mean() / 60:.1f}",
            ]
        }
    else:
        print("  ❌ No hay datos detallados para procesar.")
        return
    
    df_stats = pd.DataFrame(stats_generales)
    
    # Exportar a Excel con formato
    archivo_resumen = os.path.join(carpeta_resumen, "RESUMEN_GENERAL.xlsx")
    with pd.ExcelWriter(archivo_resumen, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name='Estadísticas Generales', index=False)
        df_resumen_usuarios.to_excel(writer, sheet_name='Resumen por Usuario', index=False)
        df_resumen_letras.to_excel(writer, sheet_name='Resumen por Letra', index=False)
        if len(df_todos_datos) > 0:
            df_todos_datos.to_excel(writer, sheet_name='Todos Los Datos Crudos', index=False)
    
    print(f"\n  ✓ Resumen general exportado a Excel:")
    print(f"    {archivo_resumen}")
    
    # Generar gráficos consolidados
    if len(df_todos_datos) > 0:
        print(f"\n  Generando gráficos de resumen...\n")
        
        fig = plt.figure(figsize=(18, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        fig.suptitle('RESUMEN CONSOLIDADO - Pruebas SIGNVOICE', 
                    fontsize=20, fontweight='bold', y=0.995)
        
        # 1. Confianza por usuario
        ax1 = fig.add_subplot(gs[0, 0])
        confianza_por_usuario = df_resumen_usuarios.groupby('usuario_id')['confianza_promedio'].mean()
        bars1 = ax1.bar(confianza_por_usuario.index, confianza_por_usuario.values, 
                       color='#2E86AB', edgecolor='black', alpha=0.7)
        ax1.set_xlabel('Usuario ID', fontweight='bold')
        ax1.set_ylabel('Confianza Promedio', fontweight='bold')
        ax1.set_title('Confianza Promedio por Usuario', fontweight='bold', fontsize=11)
        ax1.set_ylim([0, 1.05])
        ax1.grid(alpha=0.3, axis='y')
        ax1.axhline(y=df_todos_datos['confianza'].mean(), color='red', linestyle='--', 
                   linewidth=2, label=f"Global: {df_todos_datos['confianza'].mean():.3f}")
        ax1.legend()
        
        # 2. Latencia por usuario
        ax2 = fig.add_subplot(gs[0, 1])
        latencia_por_usuario = df_resumen_usuarios.groupby('usuario_id')['latencia_promedio_ms'].mean()
        bars2 = ax2.bar(latencia_por_usuario.index, latencia_por_usuario.values,
                       color='#A23B72', edgecolor='black', alpha=0.7)
        ax2.set_xlabel('Usuario ID', fontweight='bold')
        ax2.set_ylabel('Latencia Promedio (ms)', fontweight='bold')
        ax2.set_title('Latencia Promedio por Usuario', fontweight='bold', fontsize=11)
        ax2.grid(alpha=0.3, axis='y')
        ax2.axhline(y=df_todos_datos['latencia_ms'].mean(), color='red', linestyle='--',
                   linewidth=2, label=f"Global: {df_todos_datos['latencia_ms'].mean():.1f} ms")
        ax2.legend()
        
        # 3. Reconocimientos por usuario
        ax3 = fig.add_subplot(gs[0, 2])
        recon_por_usuario = df_resumen_usuarios.groupby('usuario_id')['total_reconocimientos'].sum()
        bars3 = ax3.bar(recon_por_usuario.index, recon_por_usuario.values,
                       color='#F18F01', edgecolor='black', alpha=0.7)
        ax3.set_xlabel('Usuario ID', fontweight='bold')
        ax3.set_ylabel('Total de Reconocimientos', fontweight='bold')
        ax3.set_title('Reconocimientos Totales por Usuario', fontweight='bold', fontsize=11)
        ax3.grid(alpha=0.3, axis='y')
        
        # 4. Distribución de confianza
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.hist(df_todos_datos['confianza'], bins=50, color='#2E86AB', 
                edgecolor='black', alpha=0.7)
        ax4.set_xlabel('Confianza', fontweight='bold')
        ax4.set_ylabel('Frecuencia', fontweight='bold')
        ax4.set_title('Distribución Global de Confianza', fontweight='bold', fontsize=11)
        ax4.axvline(df_todos_datos['confianza'].mean(), color='red', linestyle='--', 
                   linewidth=2, label=f"Media: {df_todos_datos['confianza'].mean():.3f}")
        ax4.axvline(df_todos_datos['confianza'].quantile(0.5), color='green', linestyle='--',
                   linewidth=2, label=f"Mediana: {df_todos_datos['confianza'].quantile(0.5):.3f}")
        ax4.legend()
        ax4.grid(alpha=0.3)
        
        # 5. Distribución de latencia
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.hist(df_todos_datos['latencia_ms'], bins=50, color='#A23B72',
                edgecolor='black', alpha=0.7)
        ax5.set_xlabel('Latencia (ms)', fontweight='bold')
        ax5.set_ylabel('Frecuencia', fontweight='bold')
        ax5.set_title('Distribución Global de Latencia', fontweight='bold', fontsize=11)
        ax5.axvline(df_todos_datos['latencia_ms'].mean(), color='red', linestyle='--',
                   linewidth=2, label=f"Media: {df_todos_datos['latencia_ms'].mean():.1f} ms")
        ax5.axvline(df_todos_datos['latencia_ms'].quantile(0.5), color='green', linestyle='--',
                   linewidth=2, label=f"Mediana: {df_todos_datos['latencia_ms'].quantile(0.5):.1f} ms")
        ax5.legend()
        ax5.grid(alpha=0.3)
        
        # 6. Box plot de confianza por usuario
        ax6 = fig.add_subplot(gs[1, 2])
        data_box_conf = [df_todos_datos[df_todos_datos['timestamp'].str.contains(f"USER{i}")] 
                        for i in sorted(df_resumen_usuarios['usuario_id'].unique())]
        if len(data_box_conf) > 0 and len(df_todos_datos) > 0:
            usuarios_ids = sorted(df_resumen_usuarios['usuario_id'].unique())
            confianzas_por_usuario = [
                [df_todos_datos.iloc[j]['confianza'] for j in range(len(df_todos_datos))
                 if str(usuarios_ids[i]) in str(j)]
                for i in range(len(usuarios_ids))
            ]
            # Usar datos agregados por usuario en su lugar
            bp = ax6.boxplot([df_resumen_usuarios[df_resumen_usuarios['usuario_id'] == uid]['confianza_promedio'].values
                            for uid in usuarios_ids],
                           labels=usuarios_ids, patch_artist=True)
            for patch in bp['boxes']:
                patch.set_facecolor('#2E86AB')
            ax6.set_xlabel('Usuario ID', fontweight='bold')
            ax6.set_ylabel('Confianza', fontweight='bold')
            ax6.set_title('Rango de Confianza por Usuario', fontweight='bold', fontsize=11)
            ax6.grid(alpha=0.3, axis='y')
        
        # 7. Confianza promedio por letra
        ax7 = fig.add_subplot(gs[2, 0])
        letras_sorted = df_resumen_letras.sort_values('Confianza Promedio', ascending=False).head(10)
        ax7.barh(letras_sorted['Letra'], letras_sorted['Confianza Promedio'],
                color='#F18F01', edgecolor='black', alpha=0.7)
        ax7.set_xlabel('Confianza Promedio', fontweight='bold')
        ax7.set_title('Top 10 Letras - Confianza', fontweight='bold', fontsize=11)
        ax7.set_xlim([0, 1.05])
        ax7.grid(alpha=0.3, axis='x')
        
        # 8. Latencia promedio por letra
        ax8 = fig.add_subplot(gs[2, 1])
        latencia_sorted = df_resumen_letras.sort_values('Latencia Promedio (ms)').head(10)
        ax8.barh(latencia_sorted['Letra'], latencia_sorted['Latencia Promedio (ms)'],
                color='#C73E1D', edgecolor='black', alpha=0.7)
        ax8.set_xlabel('Latencia Promedio (ms)', fontweight='bold')
        ax8.set_title('Top 10 Letras - Latencia Más Rápida', fontweight='bold', fontsize=11)
        ax8.grid(alpha=0.3, axis='x')
        
        # 9. Reconocimientos por letra
        ax9 = fig.add_subplot(gs[2, 2])
        letras_top = df_resumen_letras.sort_values('Total Reconocimientos', ascending=False).head(15)
        ax9.bar(letras_top['Letra'], letras_top['Total Reconocimientos'],
               color='#06A77D', edgecolor='black', alpha=0.7)
        ax9.set_xlabel('Letra', fontweight='bold')
        ax9.set_ylabel('Reconocimientos', fontweight='bold')
        ax9.set_title('Top 15 Letras - Reconocimientos', fontweight='bold', fontsize=11)
        ax9.tick_params(axis='x', rotation=0)
        ax9.grid(alpha=0.3, axis='y')
        
        archivo_grafico = os.path.join(carpeta_resumen, "GRAFICOS_RESUMEN_CONSOLIDADO.png")
        plt.savefig(archivo_grafico, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Gráficos consolidados guardados:")
        print(f"    {archivo_grafico}\n")
    
    # Imprimir resumen en consola
    print("="*70)
    print("  ESTADÍSTICAS GENERALES")
    print("="*70)
    for idx, row in df_stats.iterrows():
        if row['Métrica'] == '':
            print()
        else:
            print(f"  {row['Métrica']:<45}: {str(row['Valor']):<20}")
    print("\n" + "="*70)
    print("  RESUMEN POR LETRA")
    print("="*70)
    print(df_resumen_letras.to_string(index=False))
    print("\n" + "="*70)
    
    print(f"\n  📁 Carpeta de resumen final: {carpeta_resumen}/")
    print(f"\n  ✓ Resumen completado exitosamente.\n")


if __name__ == "__main__":
    generar_resumen_final()
