import os
import sqlite3
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.apps import apps
from django.db import models

# Import ALL possible dependency models from ALL relevant apps.
try:
    from Exp_Main.models import ExpBase as MainExpBase, ExpPath as MainExpPath, Observation, ExpType, FileEnding as MainFileEnding
    from Exp_Sub.models import (
        ExpBase as SubExp_base, ExpPath as SubExpPath, Liquid, Gas, FileEnding as SubFileEnding,
        LSP, HBK, MFL, MFR, HME, HIA, TCM, CAP
    )
    from Lab_Misc.models import SampleBase, ProjectEntry, OszScriptGen, SampleBlank, PseudoSample, SampleBrushPNiPAAmSi, Polymer, GassesScript
    from Lab_Dash.models import (
        OCA as OCA_dash, LMP as LMP_dash, RSD as RSD_dash, GRV as GRV_dash, SEL as SEL_dash, DAF as DAF_dash,
        SFG as SFG_dash, GRP as GRP_dash, KUR as KUR_dash, Comparison as Comparison_dash_model, ComparisonEntry,
        OszAnalysis as OszAnalysis_dash_model, OszAnalysisEntry, DafAnalysis as DafAnalysis_dash_model, DafAnalysisEntry,
        GrvAnalysis as GrvAnalysis_dash_model, SFG_cycle, SFG_abrastern, SFG_kin_3D, SFG_kin_drive
    )
    from Analysis.models import (
        Comparison, GrvAnalysis, GrvAnalysisJoin, SteadyShift, PointsShift,
        OszAnalysis, OszAnalysisJoin, OszBaseParam, OszFitRes, OszDerivedRes,
        DafAnalysis, LMPCosolventAnalysis
    )
    MODELS_IMPORTED = True
except ImportError:
    MODELS_IMPORTED = False

class Command(BaseCommand):
    help = 'Performs a complete "deep" data migration for any main experiment model.'

    def add_arguments(self, parser):
        parser.add_argument('model_name', type=str, help='The lowercase name of the model to migrate (e.g., sel, lmp).')
        parser.add_argument('ids', nargs='+', type=int, help='The IDs of the objects to migrate.')

    def discover_forward_dependencies(self, initial_objects, objects_to_migrate):
        """Recursively finds all related objects via FORWARD relationships and PARENT links."""
        queue = list(initial_objects)
        processed_keys = set()

        while queue:
            obj = queue.pop(0)
            obj_key = (obj.__class__, obj.pk)
            if not obj or obj_key in processed_keys:
                continue
            
            processed_keys.add(obj_key)
            objects_to_migrate[obj.__class__].add(obj.pk)

            if isinstance(obj, SubExp_base) and obj.__class__ == SubExp_base:
                try:
                    child_model_class = apps.get_model('Exp_Sub', obj.Device.Abbrev)
                    queue.append(child_model_class.objects.get(pk=obj.pk))
                except Exception: pass

            # ==============================================================================
            # CRITICAL FIX: Explicitly and correctly walk up the inheritance tree using Django's
            # internal `_meta.parents`. This guarantees finding MainExpBase from LMP, SEL, etc.
            # ==============================================================================
            for parent_model, parent_link_field in obj._meta.parents.items():
                if parent_link_field:
                    parent_obj = getattr(obj, parent_link_field.name)
                    if parent_obj:
                        queue.append(parent_obj)

            # Now, handle other standard forward relations
            for field in obj._meta.get_fields():
                # Skip reverse relations and the parent links we just handled.
                if field.auto_created or (hasattr(field, 'parent_link') and field.parent_link):
                    continue

                if field.is_relation:
                    value = getattr(obj, field.name, None)
                    if isinstance(value, models.Model):
                        queue.append(value)
                    elif isinstance(value, models.Manager):
                        for related_obj in value.all():
                            queue.append(related_obj)
            # ==============================================================================

    def discover_reverse_dependencies(self, pks_by_model, objects_to_migrate):
        """Explicitly searches for analysis models that point to already-discovered experiments."""
        self.stdout.write("\n--- Searching for reverse links from Analysis models ---")
        
        ANALYSIS_MODELS = [GrvAnalysis, LMPCosolventAnalysis, OszAnalysis, Comparison, DafAnalysis]
        
        main_exp_pks = pks_by_model.get(MainExpBase, set())
        if not main_exp_pks:
            self.stdout.write(self.style.WARNING("  -> No main experiments were discovered, so cannot search for linked analyses."))
            return

        newly_discovered_objects = []
        for analysis_model in ANALYSIS_MODELS:
            for field in analysis_model._meta.get_fields():
                if isinstance(field, (models.ForeignKey, models.ManyToManyField)) and issubclass(field.related_model, MainExpBase):
                    filter_query = {f"{field.name}__pk__in": main_exp_pks}
                    found_analyses = analysis_model.objects.filter(**filter_query).distinct()
                    if found_analyses.exists():
                        self.stdout.write(f"  -> Found {found_analyses.count()} '{analysis_model.__name__}' objects linked to experiments.")
                        newly_discovered_objects.extend(list(found_analyses))
        
        if newly_discovered_objects:
            self.stdout.write("  -> Discovering dependencies of newly found analysis objects...")
            self.discover_forward_dependencies(newly_discovered_objects, objects_to_migrate)

    def migrate_data_for_model(self, connection, model, object_ids):
        """Generic function to migrate data for a specific model."""
        if not object_ids: return
        table_name = model._meta.db_table
        self.stdout.write(f"Migrating {len(object_ids)} records for '{model.__name__}' into table '{table_name}'...")
        cursor = connection.cursor()
        try:
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            target_columns = [info[1] for info in cursor.fetchall()]
            if not target_columns:
                self.stdout.write(self.style.WARNING(f"  -> Skipping: Target table '{table_name}' not found."))
                return
        except sqlite3.Error as e:
            raise CommandError(f'Failed to read schema for table "{table_name}": {e}')
        
        db_to_field_map = {field.column: field.name for field in model._meta.get_fields() if hasattr(field, 'column')}
        try:
            fields_for_orm_query = [db_to_field_map[col] for col in target_columns]
        except KeyError as e:
            raise CommandError(f"Schema mismatch for model '{model.__name__}'. Column {e} exists in DB but not in Django model.")

        source_data = list(model.objects.filter(pk__in=object_ids).values_list(*fields_for_orm_query))
        placeholders = ", ".join(["?"] * len(target_columns))
        quoted_columns = ", ".join([f'"{col}"' for col in target_columns])
        sql_insert = f'INSERT OR IGNORE INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders});'
        cursor.executemany(sql_insert, source_data)
        connection.commit()
        self.stdout.write(self.style.SUCCESS(f"  -> Done. Affected {cursor.rowcount} rows."))

    def migrate_m2m_data(self, connection, model, object_ids):
        """Migrates data ONLY for ManyToMany fields defined directly on this model."""
        m2m_fields = [f for f in model._meta.many_to_many if f.model == model]
        if not m2m_fields or not object_ids: return

        for field in m2m_fields:
            m2m_table, m2m_col1, m2m_col2 = field.m2m_db_table(), field.m2m_column_name(), field.m2m_reverse_name()
            self.stdout.write(f"Migrating M2M links for '{model.__name__}.{field.name}' into table '{m2m_table}'...")
            cursor = connection.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{m2m_table}';")
            if not cursor.fetchone():
                self.stdout.write(self.style.WARNING(f"  -> Skipping: M2M table '{m2m_table}' not found."))
                continue
            
            through_model = field.remote_field.through
            m2m_filter = {f"{field.m2m_field_name()}__in": object_ids}
            m2m_data = list(through_model.objects.filter(**m2m_filter).values_list(m2m_col1, m2m_col2))
            if not m2m_data:
                self.stdout.write("  -> No relationships to migrate.")
                continue

            sql_insert = f'INSERT OR IGNORE INTO "{m2m_table}" ("{m2m_col1}", "{m2m_col2}") VALUES (?, ?);'
            cursor.executemany(sql_insert, m2m_data)
            connection.commit()
            self.stdout.write(self.style.SUCCESS(f"  -> Done. Affected {cursor.rowcount} rows."))

    def handle(self, *args, **options):
        model_name_str, ids = options['model_name'].lower(), options['ids']
        target_db_path = os.path.join(settings.BASE_DIR, 'db_Export.sqlite3')
        self.stdout.write(self.style.SUCCESS(f"--- Starting Full Data Migration for model '{model_name_str}' ---"))

        if not MODELS_IMPORTED: raise CommandError("Could not import all required models.")
        
        try:
            ModelClass = apps.get_model('Exp_Main', model_name_str)
        except LookupError:
            raise CommandError(f"Model '{model_name_str}' not found in 'Exp_Main' app.")
        
        if not issubclass(ModelClass, MainExpBase):
            raise CommandError(f"Model '{ModelClass.__name__}' is not a valid main experiment type.")
        
        initial_objects = ModelClass.objects.filter(id__in=ids)
        if not initial_objects.exists():
            raise CommandError(f"No objects found for model '{ModelClass.__name__}' with IDs: {ids}")

        objects_to_migrate = defaultdict(set)
        self.stdout.write("\n--- Discovering forward dependencies ---")
        self.discover_forward_dependencies(initial_objects, objects_to_migrate)
        self.discover_reverse_dependencies(objects_to_migrate, objects_to_migrate)

        self.stdout.write("\n--- Final discovery results ---")
        for model, pks in sorted(objects_to_migrate.items(), key=lambda item: item[0].__name__):
             self.stdout.write(f"  -> To migrate: {len(pks)} of '{model.__name__}'")
        
        MIGRATION_ORDER = [
            SampleBase, SampleBlank, PseudoSample, SampleBrushPNiPAAmSi, Polymer,
            MainExpPath, SubExpPath, Observation, ProjectEntry, ExpType,
            Liquid, Gas, MainFileEnding, SubFileEnding, OszScriptGen, GassesScript,
            OCA_dash, LMP_dash, RSD_dash, GRV_dash, SEL_dash, DAF_dash,
            SFG_dash, GRP_dash, KUR_dash,
            ComparisonEntry, OszAnalysisEntry, DafAnalysisEntry,
            SubExp_base, MainExpBase,
            LSP, HBK, MFL, MFR, HME, HIA, TCM, CAP,
            PointsShift, SteadyShift,
            OszBaseParam, OszFitRes, OszDerivedRes,
            GrvAnalysis, LMPCosolventAnalysis, OszAnalysis, DafAnalysis,
            Comparison, GrvAnalysisJoin, OszAnalysisJoin,
            Comparison_dash_model, OszAnalysis_dash_model, DafAnalysis_dash_model, GrvAnalysis_dash_model,
            SFG_cycle, SFG_abrastern, SFG_kin_3D, SFG_kin_drive,
            ModelClass,
        ]
        
        try:
            with sqlite3.connect(target_db_path) as target_conn:
                self.stdout.write("\n--- Migrating main table data in order ---")
                processed_models = set()
                for model_in_order in MIGRATION_ORDER:
                    if model_in_order in objects_to_migrate:
                        self.migrate_data_for_model(target_conn, model_in_order, objects_to_migrate[model_in_order])
                        processed_models.add(model_in_order)
                
                for model, pks in objects_to_migrate.items():
                    if model not in processed_models:
                        self.migrate_data_for_model(target_conn, model, pks)

                self.stdout.write("\n--- Migrating many-to-many relationship data ---")
                for model, pks in objects_to_migrate.items():
                    if pks:
                        self.migrate_m2m_data(target_conn, model, pks)

        except (sqlite3.Error, ValueError, CommandError) as e:
            raise CommandError(f"Migration failed: {e}")
        except Exception as e:
            self.stderr.write("An unexpected error occurred:")
            raise e
        
        self.stdout.write(self.style.SUCCESS(f"\n--- Full Migration for '{model_name_str}' Completed Successfully! ---"))