from collections import defaultdict
from typing import Union, Optional, List, Iterable, Mapping, Sequence
import warnings

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import scanpy as sc
from anndata import AnnData
from .._core.mudata import MuData

def _average_peaks(adata: AnnData,
				   keys: List[str],
				   average: str,
				   use_raw: bool):
	# New keys will be placed here
	attr_names = []
	tmp_names = []
	x = adata.obs.loc[:,[]]
	for key in keys:
		if key not in adata.obs_names and key not in adata.obs.columns:
			if 'atac' not in adata.uns or 'peak_annotation' not in adata.uns['atac']:
				raise KeyError(f"There is no feature or feature annotation {key}. If it is a gene name, load peak annotation with muon.atac.pp.add_peak_annotation first.")
			peak_sel = adata.uns["atac"]["peak_annotation"].loc[[key]]

			# only use peaks that are in the object (e.g. haven't been filtered out)
			peak_sel = peak_sel[peak_sel.peak.isin(adata.var_names.values)]

			peaks = peak_sel.peak

			if len(peaks) == 0:
				warnings.warn(f"Peaks for {key} are not found.")
				continue

			if average == 'total' or average == 'all':
				attr_name = f"{key} (all peaks)"
				attr_names.append(attr_name)
				tmp_names.append(attr_name)

				if attr_name not in adata.obs.columns:
					if use_raw:
						x[attr_name] = np.asarray(adata.raw[:,peaks].X.mean(axis=1)).reshape(-1)
					else:
						x[attr_name] = np.asarray(adata[:,peaks].X.mean(axis=1)).reshape(-1)

			elif average == 'peak_type':
				peak_types = peak_sel.peak_type

				# {'promoter': ['chrX:NNN_NNN', ...], 'distal': ['chrX:NNN_NNN', ...]}
				peak_dict = defaultdict(list)
				for k, v in zip(peak_types, peaks):
					peak_dict[k].append(v)

				# 'CD4 (promoter peaks)', 'CD4 (distal peaks)'
				for t, p in peak_dict.items():
					attr_name = f"{key} ({t} peaks)"
					attr_names.append(attr_name)
					tmp_names.append(attr_name)

					if attr_name not in adata.obs.columns:
						if use_raw:
							x[attr_name] = np.asarray(adata.raw[:,p].X.mean(axis=1)).reshape(-1)
						else:
							x[attr_name] = np.asarray(adata[:,p].X.mean(axis=1)).reshape(-1)

			else:
				# No averaging, one plot per peak
				if average is not None and average is not False and average != -1:
					warnings.warn(f"Plotting individual peaks since {average} was not recognised. Try using 'total' or 'peak_type'.")
				attr_names += peak_sel.peak.values
		
		else:
			attr_names.append(key)

	return (x, attr_names, tmp_names)

def embedding(data: Union[AnnData, MuData],
			  basis: str,
			  color: Optional[Union[str, List[str]]] = None,
			  average: Optional[str] = 'total',
			  use_raw: bool = True,
			  **kwargs):
	"""
	Scatter plot in the define basis

	See sc.pl.embedding for details.
	"""
	if isinstance(data, AnnData):
		adata = data
	elif isinstance(data, MuData):
		adata = data.mod['atac']
	else:
		raise TypeError("Expected AnnData or MuData object with 'atac' modality")

	if color is not None:
		if isinstance(color, str):
			keys = [color]
		elif isinstance(color, Iterable):
			keys = color
		else:
			raise TypeError("Expected color to be a string or an iterable.")

		x, attr_names, _ = _average_peaks(adata=adata, keys=keys, average=average, use_raw=use_raw)
		ad = AnnData(x, obs=adata.obs, obsm=adata.obsm)
		sc.pl.embedding(ad, basis=basis, color=attr_names, **kwargs)

		return None

	else:
		return sc.pl.embedding(adata, basis=basis, use_raw=use_raw, **kwargs)

	return None


def pca(data: Union[AnnData, MuData], **kwargs) -> Union[Axes, List[Axes], None]:
	"""
	Scatter plot for principle components

	See sc.pl.embedding for details.
	"""
	return embedding(data, basis='pca', **kwargs)


def lsi(data: Union[AnnData, MuData], **kwargs) -> Union[Axes, List[Axes], None]:
	"""
	Scatter plot for latent semantic indexing components

	See sc.pl.embedding for details.
	"""
	return embedding(data, basis='lsi', **kwargs)


def umap(data: Union[AnnData, MuData], **kwargs) -> Union[Axes, List[Axes], None]:
	"""
	Scatter plot in UMAP space

	See sc.pl.embedding for details.
	"""
	return embedding(data, basis='umap', **kwargs)


def mofa(mdata: MuData, **kwargs) -> Union[Axes, List[Axes], None]:
	"""
	Scatter plot in MOFA factors coordinates

	See sc.pl.embedding for details.
	"""
	return embedding(mdata, 'mofa', **kwargs)


def dotplot(data: Union[AnnData, MuData],
			var_names: Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]],
			groupby: Optional[Union[str]] = None,
			average: Optional[str] = 'total',
			use_raw: Optional[Union[bool]] = None,
			**kwargs):
	"""
	Dotplot

	See sc.pl.embedding for details.
	"""
	if isinstance(data, AnnData):
		adata = data
	elif isinstance(data, MuData):
		adata = data.mod['atac']
	else:
		raise TypeError("Expected AnnData or MuData object with 'atac' modality")

	if isinstance(var_names, str):
		keys = [var_names]
	elif isinstance(var_names, Iterable):
		keys = var_names
	else:
		raise TypeError("Expected var_names to be a string or an iterable.")

	x, attr_names, tmp_names = _average_peaks(adata=adata, keys=keys, average=average, use_raw=use_raw)
	ad = AnnData(x, obs=adata.obs)
	sc.pl.dotplot(ad, var_names=attr_names, groupby=groupby, use_raw=use_raw, **kwargs)

	return None


def tss_enrichment(data: AnnData,
                  groupby:str = None,
                  ax: Optional[Axes] = None):

    ax = ax or plt.gca()


    if groupby is not None:

        if isinstance(groupby, str):
            groupby = [groupby]

        groups = data.obs.groupby(groupby)

        for name, group in groups:
            ad = data[group.index]
            _tss_enrichment_single(ad, ax)
    else:
        _tss_enrichment_single(data, ax)

    # TODO Not sure how to best deal with plot returning/showing
    plt.show()
    return None

def _tss_enrichment_single(data: AnnData,
                           ax: Axes,
                           sd: bool=False):
    x = data.var['TSS_position']
    means = data.X.mean(axis=0)
    ax.plot(x , means)
    if sd:
        sd = np.sqrt(data.X.var(axis=0))
        plt.fill_between(
            x,
            means - sd,
            means + sd,
            alpha=0.2,
        )
