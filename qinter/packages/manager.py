"""
qinter/packages/manager.py
"""

import shutil
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from qinter.packages.registry_client import get_registry_client
from qinter.packages.loader import get_loader
from qinter.config.settings import get_settings
from qinter.utils.exceptions import PackageError


class PackageManager:
    """Manages explanation pack installation and removal."""
    
    def __init__(self):
        self.registry_client = get_registry_client()
        self.loader = get_loader()
        self.settings = get_settings()
    
    def search_packs(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for packs in the registry.
        
        Args:
            query: Search query
            
        Returns:
            List of matching packs
        """
        return self.registry_client.search_packs(query)
    
    def list_installed_packs(self) -> List[Dict[str, Any]]:
        """
        List all installed explanation packs.
        
        Returns:
            List of installed pack information
        """
        installed = []
        packages_dir = self._get_packages_directory()
        
        if not packages_dir.exists():
            return installed
        
        for pack_file in packages_dir.glob("*.yaml"):
            try:
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack_data = yaml.safe_load(f)
                
                metadata = pack_data.get('metadata', {})
                installed.append({
                    'name': metadata.get('name', pack_file.stem),
                    'version': metadata.get('version', 'unknown'),
                    'description': metadata.get('description', 'No description'),
                    'author': metadata.get('author', 'Unknown'),
                    'license': metadata.get('license', 'Unknown'),
                    'tags': metadata.get('tags', []),
                    'targets': metadata.get('targets', []),
                    'qinter_version': metadata.get('qinter_version', '>=1.0.0'),
                    'file_path': str(pack_file),
                    'file_size': pack_file.stat().st_size,
                    'installed_at': pack_file.stat().st_mtime
                })
                
            except Exception as e:
                print(f"⚠️  Warning: Failed to read pack {pack_file}: {e}")
        
        return sorted(installed, key=lambda x: x['name'])
    
    def install_pack(self, pack_name: str, version: str = "latest") -> bool:
        """
        Install an explanation pack.
        
        Args:
            pack_name: Name of the pack to install
            version: Version to install (default: latest)
            
        Returns:
            True if installation successful, False otherwise
        """
        try:
            # Check if pack already exists
            if self.is_pack_installed(pack_name):
                installed_version = self.get_installed_version(pack_name)
                print(f"📦 Pack '{pack_name}' version {installed_version} is already installed")
                
                # Check if we should update
                pack_info = self.get_pack_info(pack_name)
                if pack_info and pack_info.get('version') != installed_version:
                    print(f"🔄 Newer version {pack_info.get('version')} available")
                    return self._update_pack(pack_name, version)
                
                return True
            
            # Download pack from registry
            print(f"📥 Downloading '{pack_name}' from registry...")
            pack_content = self.registry_client.download_pack(pack_name, version)
            
            if not pack_content:
                print(f"❌ Pack '{pack_name}' not found in registry")
                return False
            
            # Validate pack content
            try:
                pack_data = yaml.safe_load(pack_content)
                self._validate_pack_data(pack_data, pack_name)
            except yaml.YAMLError as e:
                raise PackageError(f"Invalid YAML in pack '{pack_name}': {e}")
            
            # Save pack to local packages directory
            pack_file = self._get_pack_file_path(pack_name)
            pack_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(pack_file, 'w', encoding='utf-8') as f:
                f.write(pack_content)
            
            print(f"✅ Successfully installed '{pack_name}' version {pack_data['metadata']['version']}")
            
            # Reload explanation engine to include new pack
            self._reload_explanations()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to install '{pack_name}': {e}")
            return False
    
    def uninstall_pack(self, pack_name: str) -> bool:
        """
        Uninstall an explanation pack.
        
        Args:
            pack_name: Name of the pack to uninstall
            
        Returns:
            True if uninstallation successful, False otherwise
        """
        try:
            if not self.is_pack_installed(pack_name):
                print(f"📦 Pack '{pack_name}' is not installed")
                return False
            
            # Remove pack file
            pack_file = self._get_pack_file_path(pack_name)
            pack_file.unlink()
            
            print(f"✅ Successfully uninstalled '{pack_name}'")
            
            # Reload explanation engine
            self._reload_explanations()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to uninstall '{pack_name}': {e}")
            return False
    
    def get_pack_info(self, pack_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a pack.
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            Pack information or None if not found
        """
        # Check if installed locally first
        if self.is_pack_installed(pack_name):
            pack_file = self._get_pack_file_path(pack_name)
            try:
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack_data = yaml.safe_load(f)
                    
                info = pack_data.get('metadata', {}).copy()
                info['status'] = 'installed'
                info['file_path'] = str(pack_file)
                info['file_size'] = f"{pack_file.stat().st_size} bytes"
                info['installed_at'] = pack_file.stat().st_mtime
                return info
                
            except Exception as e:
                print(f"⚠️  Warning: Failed to read installed pack {pack_name}: {e}")
        
        # Get info from registry
        return self.registry_client.get_pack_info(pack_name)
    
    def update_pack(self, pack_name: str) -> bool:
        """
        Update an installed pack to the latest version.
        
        Args:
            pack_name: Name of the pack to update
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.is_pack_installed(pack_name):
            print(f"📦 Pack '{pack_name}' is not installed")
            return False
        
        return self._update_pack(pack_name, "latest")
    
    def update_all_packs(self) -> Dict[str, bool]:
        """
        Update all installed packs.
        
        Returns:
            Dictionary mapping pack names to update success status
        """
        installed_packs = self.list_installed_packs()
        results = {}
        
        if not installed_packs:
            print("📦 No packs installed to update")
            return results
        
        print(f"🔄 Updating {len(installed_packs)} installed packs...")
        
        for pack in installed_packs:
            pack_name = pack['name']
            print(f"\n🔄 Checking updates for {pack_name}...")
            
            # Get latest version info
            latest_info = self.registry_client.get_pack_info(pack_name)
            if not latest_info:
                print(f"⚠️  Could not check updates for {pack_name}")
                results[pack_name] = False
                continue
            
            current_version = pack['version']
            latest_version = latest_info.get('version', 'unknown')
            
            if current_version == latest_version:
                print(f"✅ {pack_name} is already up to date (v{current_version})")
                results[pack_name] = True
            else:
                print(f"📥 Updating {pack_name} from v{current_version} to v{latest_version}")
                results[pack_name] = self._update_pack(pack_name, "latest")
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        print(f"\n📊 Update Summary: {successful}/{len(results)} packs updated successfully")
        
        return results
    
    def check_pack_updates(self) -> List[Dict[str, Any]]:
        """
        Check which installed packs have updates available.
        
        Returns:
            List of packs with available updates
        """
        installed_packs = self.list_installed_packs()
        updates_available = []
        
        for pack in installed_packs:
            pack_name = pack['name']
            current_version = pack['version']
            
            # Get latest version info
            latest_info = self.registry_client.get_pack_info(pack_name)
            if latest_info:
                latest_version = latest_info.get('version', 'unknown')
                
                if current_version != latest_version:
                    updates_available.append({
                        'name': pack_name,
                        'current_version': current_version,
                        'latest_version': latest_version,
                        'description': latest_info.get('description', ''),
                        'changelog': latest_info.get('changelog', 'No changelog available')
                    })
        
        return updates_available
    
    def validate_pack(self, pack_name: str) -> Dict[str, Any]:
        """
        Validate an installed pack.
        
        Args:
            pack_name: Name of the pack to validate
            
        Returns:
            Validation results
        """
        if not self.is_pack_installed(pack_name):
            return {
                'valid': False,
                'errors': [f"Pack '{pack_name}' is not installed"]
            }
        
        pack_file = self._get_pack_file_path(pack_name)
        
        try:
            with open(pack_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate YAML syntax
            try:
                pack_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                return {
                    'valid': False,
                    'errors': [f"Invalid YAML syntax: {e}"]
                }
            
            # Validate pack structure
            errors = []
            self._validate_pack_data(pack_data, pack_name)
            
            # Additional validation using our validation utility
            from qinter.utils.validation import get_validation_errors
            validation_errors = get_validation_errors(content)
            errors.extend(validation_errors)
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': []  # Could add warnings for non-critical issues
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation failed: {e}"]
            }
    
    def get_pack_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about installed packs.
        
        Returns:
            Statistics dictionary
        """
        installed_packs = self.list_installed_packs()
        
        if not installed_packs:
            return {
                'total_packs': 0,
                'total_size': 0,
                'exception_types_covered': [],
                'authors': [],
                'licenses': [],
                'tags': []
            }
        
        # Calculate statistics
        total_size = sum(pack.get('file_size', 0) for pack in installed_packs)
        exception_types = set()
        authors = set()
        licenses = set()
        tags = set()
        
        for pack in installed_packs:
            exception_types.update(pack.get('targets', []))
            authors.add(pack.get('author', 'Unknown'))
            licenses.add(pack.get('license', 'Unknown'))
            tags.update(pack.get('tags', []))
        
        return {
            'total_packs': len(installed_packs),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'exception_types_covered': sorted(list(exception_types)),
            'exception_types_count': len(exception_types),
            'authors': sorted(list(authors)),
            'authors_count': len(authors),
            'licenses': sorted(list(licenses)),
            'tags': sorted(list(tags)),
            'tags_count': len(tags)
        }
    
    def cleanup_cache(self) -> bool:
        """
        Clean up any cached data or temporary files.
        
        Returns:
            True if cleanup successful
        """
        try:
            # Clean up any temporary files in .qinter directory
            qinter_dir = Path.home() / ".qinter"
            temp_files = qinter_dir.glob("*.tmp")
            
            cleaned_count = 0
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                    cleaned_count += 1
                except Exception:
                    continue
            
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} temporary files")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Cleanup failed: {e}")
            return False
    
    def is_pack_installed(self, pack_name: str) -> bool:
        """Check if a pack is installed locally."""
        pack_file = self._get_pack_file_path(pack_name)
        return pack_file.exists()
    
    def get_installed_version(self, pack_name: str) -> Optional[str]:
        """Get the version of an installed pack."""
        if not self.is_pack_installed(pack_name):
            return None
        
        pack_file = self._get_pack_file_path(pack_name)
        try:
            with open(pack_file, 'r', encoding='utf-8') as f:
                pack_data = yaml.safe_load(f)
                return pack_data.get('metadata', {}).get('version')
        except Exception:
            return None
    
    def _update_pack(self, pack_name: str, version: str) -> bool:
        """Internal method to update a pack."""
        try:
            print(f"🔄 Updating '{pack_name}' to version {version}...")
            
            # Download new version
            pack_content = self.registry_client.download_pack(pack_name, version)
            
            if not pack_content:
                print(f"❌ Could not download update for '{pack_name}'")
                return False
            
            # Validate new content
            try:
                pack_data = yaml.safe_load(pack_content)
                self._validate_pack_data(pack_data, pack_name)
            except yaml.YAMLError as e:
                print(f"❌ Invalid YAML in updated pack '{pack_name}': {e}")
                return False
            
            # Backup current version
            pack_file = self._get_pack_file_path(pack_name)
            backup_file = pack_file.with_suffix('.yaml.backup')
            
            try:
                if pack_file.exists():
                    shutil.copy2(pack_file, backup_file)
                
                # Write new version
                with open(pack_file, 'w', encoding='utf-8') as f:
                    f.write(pack_content)
                
                # Remove backup if successful
                if backup_file.exists():
                    backup_file.unlink()
                
                new_version = pack_data['metadata']['version']
                print(f"✅ Successfully updated '{pack_name}' to version {new_version}")
                
                # Reload explanation engine
                self._reload_explanations()
                
                return True
                
            except Exception as e:
                # Restore backup if update failed
                if backup_file.exists():
                    shutil.copy2(backup_file, pack_file)
                    backup_file.unlink()
                    print(f"🔄 Restored backup for '{pack_name}'")
                
                raise e
                
        except Exception as e:
            print(f"❌ Failed to update '{pack_name}': {e}")
            return False
    
    def _get_packages_directory(self) -> Path:
        """Get the local packages directory."""
        packages_dir = Path.home() / ".qinter" / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        return packages_dir
    
    def _get_pack_file_path(self, pack_name: str) -> Path:
        """Get the file path for a pack."""
        return self._get_packages_directory() / f"{pack_name}.yaml"
    
    def _validate_pack_data(self, pack_data: Dict[str, Any], pack_name: str) -> None:
        """Validate pack data structure."""
        if 'metadata' not in pack_data:
            raise PackageError(f"Pack '{pack_name}' missing metadata section")
        
        metadata = pack_data['metadata']
        required_fields = ['name', 'version', 'description', 'author', 'targets']
        
        for field in required_fields:
            if field not in metadata:
                raise PackageError(f"Pack '{pack_name}' missing required field: {field}")
        
        if 'explanations' not in pack_data:
            raise PackageError(f"Pack '{pack_name}' missing explanations section")
        
        if not isinstance(pack_data['explanations'], list):
            raise PackageError(f"Pack '{pack_name}' explanations must be a list")
        
        if len(pack_data['explanations']) == 0:
            raise PackageError(f"Pack '{pack_name}' must contain at least one explanation")
    
    def _reload_explanations(self) -> None:
        """Reload the explanation engine with new packs."""
        try:
            from qinter.explanations.engine import get_engine
            engine = get_engine()
            engine.reload_packs()
            print("🔄 Explanation engine reloaded")
        except Exception as e:
            print(f"⚠️  Warning: Failed to reload explanations: {e}")


# Global package manager instance
_manager = PackageManager()

def get_package_manager() -> PackageManager:
    """Get the global package manager instance."""
    return _manager