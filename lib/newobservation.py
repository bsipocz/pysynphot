"""This will ultimately replace the observation.py module. It defines
a new Observation class, subclassed from CompositeSourceSpectrum,
that has some special methods and attributes and explicitly removes
certain other methods."""

import spectrum
import units
import numpy as N
import math

class Observation(spectrum.CompositeSourceSpectrum):
    """An Observation is the end point of a chain of spectral manipulation.
    The normal means of creating an Observation is by means of the .observe
    method on a SpectralElement."""

    def __init__(self,spec,band,binset=None):
        """The normal means of producing an Observation is by means of the
        .observe() method on the spectral element."""

        spectrum.CompositeSourceSpectrum.__init__(self, spec, band, 'multiply')
        self.spectrum = self.component1
        self.bandpass = self.component2

        #The natural waveset of the observation is the merge of the
        #natural waveset of the spectrum with the natural waveset of the
        #bandpass. Because the Observation inherits from a
        #CompositeSourceSpectrum, this will be handled correctly.

        self.initbinset(binset)
        self.initbinflux()

    def initbinset(self,binset=None):
        if binset == None:
            try:
                self.binwave = self.bandpass.obsmode.bandWave()
            except (KeyError, AttributeError), e:
                print "%s does not have a defined binset in the wavecat table. You must provide a binset."%self.bandpass
                raise e
        else:
            self.binwave=binset


    def initbinflux(self):
        """This routine performs the integration of the spectrum
        on the specified binned waveset. It uses the natural waveset
        of the spectrum in performing this integration."""

        # compute endpoints of each summation bin.
        midpoints = (self.binwave[1:] + self.binwave[:-1]) / 2.0
        endpoints = N.empty(shape=[len(midpoints)+2,],dtype=N.float64)
        endpoints[1:-1] = midpoints
        endpoints[0]  = self.binwave[0] - (midpoints[0] - self.binwave[0])
        endpoints[-1] = self.binwave[-1] + (self.binwave[-1] - midpoints[-1])

        # merge the endpoints in with the natural waveset 
        spwave = spectrum.MergeWaveSets(self.wave, endpoints)
        #spwave = spectrum.MergeWaveSets(spwave,self.binwave)

        # compute indices associated to each endpoint.
        indices = N.searchsorted(spwave, endpoints)
        diff = indices[1:] - indices[:-1]
        self._indices = indices[:-1]
        self._indices_last = self._indices + diff 

        # prepare integration variables.
        flux = self(spwave) 
        avflux = (flux[1:] + flux[:-1]) / 2.0
        self._deltaw = spwave[1:] - spwave[:-1]
        
        # sum over each bin.
        self._binflux = N.empty(shape=self.binwave.shape,dtype=N.float64)
        for i in range(len(self._indices)):
            first = self._indices[i]
            last = self._indices_last[i]
            self._binflux[i]=(avflux[first:last]*self._deltaw[first:last]).sum()/self._deltaw[first:last].sum()

    def _getBinfluxProp(self):
        binflux = units.Photlam().Convert(self.binwave,
                                          self._binflux,
                                          self.fluxunits.name)
        return binflux
    
    binflux = property(_getBinfluxProp,doc='Flux on binned wavelength set property')
 
    #Disable methods that should not be supported by this class
    def __mul__(self, other):
        raise NotImplementedError('Observations cannot be multiplied')
    def __rmul__(self, other):
        raise NotImplementedError('Observations cannot be multiplied')
    def __add__(self, other):
        raise NotImplementedError('Observations cannot be added')
    def __radd__(self, other):
        raise NotImplementedError('Observations cannot be added')
    def redshift(self,z):
        raise NotImplementedError('Observations cannot be redshifted')

    #Add methods to support ETCs
    def countrate(self):
        myfluxunits = self.fluxunits.name
        self.convert('counts')
        ans = self.trapezoidIntegration(self.wave, self.flux)
        ans*=self.bandpass.obsmode.area
        self.convert(myfluxunits)
        return ans

    def pivot(self):
        """Does this need to be calculated on binned waveset, or may
        it be calculated on native waveset?"""
        wave = self.wave

        countmulwave = self(wave)*wave
        countdivwave = self(wave)/wave

        num = self.trapezoidIntegration(wave,countmulwave)
        den = self.trapezoidIntegration(wave,countdivwave)

        return math.sqrt(num/den)