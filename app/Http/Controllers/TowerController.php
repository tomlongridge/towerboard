<?php

namespace App\Http\Controllers;

use \Cache;

use App\Tower;
use Illuminate\Http\Request;

class TowerController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {
        $towers = collect();
        if (Cache::has('towers')) {
            $towers = Cache::get('towers');
        } else {
            $towers = Cache::remember('towers', (60 * 24), function () {
                $dbTowers = Tower::all();
                $dbTowers = $dbTowers->map(function ($tower) {
                    $tower['name'] = $tower->getName();
                    return $tower;
                });
                return $dbTowers;
            });
        }

        $filterString = $request->query('q');
        if ($filterString) {
            $towers = $towers->filter(function ($value, $key) use ($filterString) {
                return stripos($value->name, $filterString) > -1;
            });
        }

        return response()->json($towers);
    }
}
